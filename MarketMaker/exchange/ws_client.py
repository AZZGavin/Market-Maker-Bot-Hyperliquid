"""
Bybit WebSocket client for market data and private updates
"""
import asyncio
import json
import time
import hmac
import hashlib
from typing import Dict, Callable, Optional, Any
from collections import defaultdict

import websockets
from loguru import logger


class BybitWebSocketClient:
    """Async WebSocket client for Bybit"""
    
    # WebSocket endpoints
    MAINNET_PUBLIC_WS = "wss://stream.bybit.com/v5/public/linear"
    TESTNET_PUBLIC_WS = "wss://stream-testnet.bybit.com/v5/public/linear"
    
    MAINNET_PRIVATE_WS = "wss://stream.bybit.com/v5/private"
    TESTNET_PRIVATE_WS = "wss://stream-testnet.bybit.com/v5/private"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        testnet: bool = True
    ):
        """
        Initialize WebSocket client
        
        Args:
            api_key: Bybit API key (for private streams)
            api_secret: Bybit API secret (for private streams)
            testnet: Use testnet if True
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        
        self.public_url = self.TESTNET_PUBLIC_WS if testnet else self.MAINNET_PUBLIC_WS
        self.private_url = self.TESTNET_PRIVATE_WS if testnet else self.MAINNET_PRIVATE_WS
        
        # WebSocket connections
        self.public_ws = None
        self.private_ws = None
        
        # Callbacks
        self.callbacks: Dict[str, list] = defaultdict(list)
        
        # Connection state
        self.public_connected = False
        self.private_connected = False
        self.running = False
        
        # Reconnection
        self.reconnect_delay = 5
        self.max_reconnect_attempts = 10
        
        # Ping/pong
        self.ping_interval = 20
        self.last_pong_time = time.time()
        
        logger.info(f"Bybit WebSocket client initialized ({'testnet' if testnet else 'mainnet'})")
    
    def _generate_auth_signature(self, expires: int) -> str:
        """
        Generate authentication signature
        
        Args:
            expires: Expiration timestamp in milliseconds
            
        Returns:
            Hex signature
        """
        sign_str = f"GET/realtime{expires}"
        
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            sign_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def on(self, topic: str, callback: Callable):
        """
        Register callback for topic
        
        Args:
            topic: Topic name (e.g., 'orderbook', 'order', 'position')
            callback: Async callback function
        """
        self.callbacks[topic].append(callback)
        logger.debug(f"Registered callback for topic: {topic}")
    
    async def _handle_message(self, message: Dict[str, Any], is_private: bool = False):
        """
        Handle incoming WebSocket message
        
        Args:
            message: Parsed message
            is_private: Whether from private stream
        """
        # Handle pong
        if message.get("op") == "pong":
            self.last_pong_time = time.time()
            return
        
        # Handle subscription confirmation
        if message.get("op") == "subscribe":
            logger.info(f"Subscribed to: {message.get('success')}")
            return
        
        # Handle auth response
        if message.get("op") == "auth":
            if message.get("success"):
                logger.info("Private WebSocket authenticated")
                self.private_connected = True
            else:
                logger.error(f"Private WebSocket auth failed: {message}")
            return
        
        # Handle data messages
        topic = message.get("topic", "")
        data = message.get("data")
        
        if not topic or not data:
            return
        
        # Route to appropriate callbacks
        if "orderbook" in topic:
            for callback in self.callbacks.get("orderbook", []):
                await callback(data)
        
        elif "order" in topic:
            for callback in self.callbacks.get("order", []):
                await callback(data)
        
        elif "position" in topic:
            for callback in self.callbacks.get("position", []):
                await callback(data)
        
        elif "execution" in topic:
            for callback in self.callbacks.get("execution", []):
                await callback(data)
    
    async def _public_stream_handler(self):
        """Handle public WebSocket stream"""
        reconnect_count = 0
        
        while self.running:
            try:
                async with websockets.connect(self.public_url) as ws:
                    self.public_ws = ws
                    self.public_connected = True
                    reconnect_count = 0
                    
                    logger.info("Public WebSocket connected")
                    
                    # Start ping task
                    ping_task = asyncio.create_task(self._ping_loop(ws))
                    
                    # Message loop
                    async for message in ws:
                        if not self.running:
                            break
                        
                        try:
                            data = json.loads(message)
                            await self._handle_message(data, is_private=False)
                        except Exception as e:
                            logger.error(f"Error handling public message: {e}")
                    
                    ping_task.cancel()
                    
            except Exception as e:
                self.public_connected = False
                reconnect_count += 1
                
                logger.error(f"Public WebSocket error: {e}")
                
                if reconnect_count >= self.max_reconnect_attempts:
                    logger.error("Max reconnection attempts reached for public stream")
                    break
                
                delay = min(self.reconnect_delay * (2 ** reconnect_count), 60)
                logger.info(f"Reconnecting public stream in {delay}s...")
                await asyncio.sleep(delay)
    
    async def _private_stream_handler(self):
        """Handle private WebSocket stream"""
        if not self.api_key or not self.api_secret:
            logger.warning("No API credentials, skipping private stream")
            return
        
        reconnect_count = 0
        
        while self.running:
            try:
                async with websockets.connect(self.private_url) as ws:
                    self.private_ws = ws
                    
                    logger.info("Private WebSocket connected, authenticating...")
                    
                    # Authenticate
                    expires = int((time.time() + 10) * 1000)
                    signature = self._generate_auth_signature(expires)
                    
                    auth_message = {
                        "op": "auth",
                        "args": [self.api_key, expires, signature]
                    }
                    
                    await ws.send(json.dumps(auth_message))
                    
                    # Start ping task
                    ping_task = asyncio.create_task(self._ping_loop(ws))
                    
                    # Message loop
                    async for message in ws:
                        if not self.running:
                            break
                        
                        try:
                            data = json.loads(message)
                            await self._handle_message(data, is_private=True)
                        except Exception as e:
                            logger.error(f"Error handling private message: {e}")
                    
                    ping_task.cancel()
                    
            except Exception as e:
                self.private_connected = False
                reconnect_count += 1
                
                logger.error(f"Private WebSocket error: {e}")
                
                if reconnect_count >= self.max_reconnect_attempts:
                    logger.error("Max reconnection attempts reached for private stream")
                    break
                
                delay = min(self.reconnect_delay * (2 ** reconnect_count), 60)
                logger.info(f"Reconnecting private stream in {delay}s...")
                await asyncio.sleep(delay)
    
    async def _ping_loop(self, ws):
        """Send periodic pings"""
        while self.running:
            try:
                await ws.send(json.dumps({"op": "ping"}))
                await asyncio.sleep(self.ping_interval)
            except Exception as e:
                logger.error(f"Ping error: {e}")
                break
    
    async def subscribe_orderbook(self, symbol: str, depth: int = 25):
        """
        Subscribe to orderbook updates
        
        Args:
            symbol: Trading symbol
            depth: Orderbook depth (1, 25, 50, 100, 200)
        """
        if not self.public_ws:
            logger.warning("Public WebSocket not connected")
            return
        
        subscribe_msg = {
            "op": "subscribe",
            "args": [f"orderbook.{depth}.{symbol}"]
        }
        
        await self.public_ws.send(json.dumps(subscribe_msg))
        logger.info(f"Subscribed to orderbook: {symbol} (depth {depth})")
    
    async def subscribe_trades(self, symbol: str):
        """
        Subscribe to trade updates
        
        Args:
            symbol: Trading symbol
        """
        if not self.public_ws:
            logger.warning("Public WebSocket not connected")
            return
        
        subscribe_msg = {
            "op": "subscribe",
            "args": [f"publicTrade.{symbol}"]
        }
        
        await self.public_ws.send(json.dumps(subscribe_msg))
        logger.info(f"Subscribed to trades: {symbol}")
    
    async def subscribe_orders(self):
        """Subscribe to order updates"""
        if not self.private_ws or not self.private_connected:
            logger.warning("Private WebSocket not connected/authenticated")
            return
        
        subscribe_msg = {
            "op": "subscribe",
            "args": ["order"]
        }
        
        await self.private_ws.send(json.dumps(subscribe_msg))
        logger.info("Subscribed to order updates")
    
    async def subscribe_positions(self):
        """Subscribe to position updates"""
        if not self.private_ws or not self.private_connected:
            logger.warning("Private WebSocket not connected/authenticated")
            return
        
        subscribe_msg = {
            "op": "subscribe",
            "args": ["position"]
        }
        
        await self.private_ws.send(json.dumps(subscribe_msg))
        logger.info("Subscribed to position updates")
    
    async def subscribe_executions(self):
        """Subscribe to execution (fill) updates"""
        if not self.private_ws or not self.private_connected:
            logger.warning("Private WebSocket not connected/authenticated")
            return
        
        subscribe_msg = {
            "op": "subscribe",
            "args": ["execution"]
        }
        
        await self.private_ws.send(json.dumps(subscribe_msg))
        logger.info("Subscribed to execution updates")
    
    async def start(self):
        """Start WebSocket streams"""
        self.running = True
        
        tasks = [
            asyncio.create_task(self._public_stream_handler()),
        ]
        
        if self.api_key and self.api_secret:
            tasks.append(asyncio.create_task(self._private_stream_handler()))
        
        logger.info("WebSocket streams started")
        
        # Wait for connections
        await asyncio.sleep(2)
    
    async def stop(self):
        """Stop WebSocket streams"""
        self.running = False
        
        if self.public_ws:
            await self.public_ws.close()
        
        if self.private_ws:
            await self.private_ws.close()
        
        logger.info("WebSocket streams stopped")
