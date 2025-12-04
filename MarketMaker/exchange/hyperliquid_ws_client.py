"""
Hyperliquid WebSocket client for market data
"""
import asyncio
import json
import time
from typing import Dict, Callable, Optional, Any
from collections import defaultdict

import websockets
from loguru import logger


class HyperliquidWebSocketClient:
    """Async WebSocket client for Hyperliquid"""
    
    # WebSocket endpoints
    MAINNET_WS = "wss://api.hyperliquid.xyz/ws"
    TESTNET_WS = "wss://api.hyperliquid-testnet.xyz/ws"
    
    def __init__(self, testnet: bool = True):
        """
        Initialize WebSocket client
        
        Args:
            testnet: Use testnet if True
        """
        self.testnet = testnet
        self.ws_url = self.TESTNET_WS if testnet else self.MAINNET_WS
        
        # WebSocket connection
        self.ws = None
        
        # Callbacks
        self.callbacks: Dict[str, list] = defaultdict(list)
        
        # Connection state
        self.connected = False
        self.running = False
        
        # Reconnection
        self.reconnect_delay = 5
        self.max_reconnect_attempts = 10
        
        # Ping/pong
        self.ping_interval = 20
        self.last_pong_time = time.time()
        
        logger.info(f"Hyperliquid WebSocket client initialized ({'testnet' if testnet else 'mainnet'})")
    
    def on(self, topic: str, callback: Callable):
        """
        Register callback for topic
        
        Args:
            topic: Topic name (e.g., 'l2Book', 'trades', 'user')
            callback: Async callback function
        """
        self.callbacks[topic].append(callback)
        logger.debug(f"Registered callback for topic: {topic}")
    
    async def _handle_message(self, message: Dict[str, Any]):
        """
        Handle incoming WebSocket message
        
        Args:
            message: Parsed message
        """
        channel = message.get("channel")
        data = message.get("data")
        
        if not channel or not data:
            return
        
        # Route to appropriate callbacks
        if channel == "l2Book":
            for callback in self.callbacks.get("orderbook", []):
                await callback(data)
        
        elif channel == "trades":
            for callback in self.callbacks.get("trades", []):
                await callback(data)
        
        elif channel == "user":
            # User events include fills, orders, positions
            for callback in self.callbacks.get("user", []):
                await callback(data)
    
    async def _stream_handler(self):
        """Handle WebSocket stream"""
        reconnect_count = 0
        
        while self.running:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    self.ws = ws
                    self.connected = True
                    reconnect_count = 0
                    
                    logger.info("Hyperliquid WebSocket connected")
                    
                    # Start ping task
                    ping_task = asyncio.create_task(self._ping_loop(ws))
                    
                    # Message loop
                    async for message in ws:
                        if not self.running:
                            break
                        
                        try:
                            data = json.loads(message)
                            await self._handle_message(data)
                        except Exception as e:
                            logger.error(f"Error handling message: {e}")
                    
                    ping_task.cancel()
                    
            except Exception as e:
                self.connected = False
                reconnect_count += 1
                
                logger.error(f"WebSocket error: {e}")
                
                if reconnect_count >= self.max_reconnect_attempts:
                    logger.error("Max reconnection attempts reached")
                    break
                
                delay = min(self.reconnect_delay * (2 ** reconnect_count), 60)
                logger.info(f"Reconnecting in {delay}s...")
                await asyncio.sleep(delay)
    
    async def _ping_loop(self, ws):
        """Send periodic pings"""
        while self.running:
            try:
                await ws.send(json.dumps({"method": "ping"}))
                await asyncio.sleep(self.ping_interval)
            except Exception as e:
                logger.error(f"Ping error: {e}")
                break
    
    async def subscribe_orderbook(self, coin: str):
        """
        Subscribe to orderbook updates
        
        Args:
            coin: Trading pair (e.g., "ETH")
        """
        if not self.ws:
            logger.warning("WebSocket not connected")
            return
        
        subscribe_msg = {
            "method": "subscribe",
            "subscription": {
                "type": "l2Book",
                "coin": coin
            }
        }
        
        await self.ws.send(json.dumps(subscribe_msg))
        logger.info(f"Subscribed to orderbook: {coin}")
    
    async def subscribe_trades(self, coin: str):
        """
        Subscribe to trade updates
        
        Args:
            coin: Trading pair
        """
        if not self.ws:
            logger.warning("WebSocket not connected")
            return
        
        subscribe_msg = {
            "method": "subscribe",
            "subscription": {
                "type": "trades",
                "coin": coin
            }
        }
        
        await self.ws.send(json.dumps(subscribe_msg))
        logger.info(f"Subscribed to trades: {coin}")
    
    async def subscribe_user_events(self, user: str):
        """
        Subscribe to user events (fills, orders, positions)
        
        Args:
            user: User address
        """
        if not self.ws:
            logger.warning("WebSocket not connected")
            return
        
        subscribe_msg = {
            "method": "subscribe",
            "subscription": {
                "type": "userEvents",
                "user": user
            }
        }
        
        await self.ws.send(json.dumps(subscribe_msg))
        logger.info(f"Subscribed to user events: {user}")
    
    async def start(self):
        """Start WebSocket stream"""
        self.running = True
        
        asyncio.create_task(self._stream_handler())
        
        logger.info("WebSocket stream started")
        
        # Wait for connection
        await asyncio.sleep(2)
    
    async def stop(self):
        """Stop WebSocket stream"""
        self.running = False
        
        if self.ws:
            await self.ws.close()
        
        logger.info("WebSocket stream stopped")
