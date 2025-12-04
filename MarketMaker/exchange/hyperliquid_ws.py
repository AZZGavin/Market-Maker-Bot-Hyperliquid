"""
Hyperliquid WebSocket client using official SDK with AsyncIO bridge
"""
import asyncio
from typing import Dict, Callable, Any, Optional
from collections import defaultdict
from loguru import logger
from hyperliquid.info import Info


class HyperliquidWebSocket:
    """WebSocket client for Hyperliquid with AsyncIO compatibility"""
    
    def __init__(self, testnet: bool = True):
        """
        Initialize WebSocket client
        
        Args:
            testnet: Use testnet if True
        """
        self.testnet = testnet
        
        # Determine base URL
        from hyperliquid.utils import constants
        if testnet:
            base_url = constants.TESTNET_API_URL
        else:
            base_url = constants.MAINNET_API_URL
        
        # Initialize Info client with WebSocket
        self.info = Info(base_url=base_url, skip_ws=False)
        
        # Callbacks
        self.callbacks: Dict[str, list] = defaultdict(list)
        
        # Event loop for async callbacks
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Subscription tracking
        self.subscriptions = []
        
        # Connection state
        self.connected = False
        self.running = False
        
        logger.info(f"Hyperliquid WebSocket initialized ({'testnet' if testnet else 'mainnet'})")
    
    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        """
        Set the event loop for async callbacks
        
        Args:
            loop: AsyncIO event loop
        """
        self.loop = loop
        logger.debug("Event loop set for WebSocket")
    
    def _create_sync_wrapper(self, async_callback: Callable) -> Callable:
        """
        Create a sync wrapper for async callback
        
        Args:
            async_callback: Async callback function
            
        Returns:
            Sync wrapper function
        """
        def sync_wrapper(data):
            """Sync wrapper that schedules async callback"""
            if self.loop and self.loop.is_running():
                # Schedule coroutine in the main event loop
                asyncio.run_coroutine_threadsafe(
                    async_callback(data),
                    self.loop
                )
            else:
                logger.warning("Event loop not available for callback")
        
        return sync_wrapper
    
    def on(self, topic: str, callback: Callable):
        """
        Register callback for topic
        
        Args:
            topic: Topic name
            callback: Async callback function
        """
        self.callbacks[topic].append(callback)
        logger.debug(f"Registered callback for topic: {topic}")
    
    async def start(self):
        """Start WebSocket"""
        # Get current event loop
        self.loop = asyncio.get_event_loop()
        
        self.running = True
        self.connected = True
        logger.info("WebSocket started")
    
    async def subscribe_orderbook(self, coin: str):
        """
        Subscribe to orderbook updates
        
        Args:
            coin: Trading pair
        """
        # Create sync wrapper for async callbacks
        def combined_callback(data):
            """Combined sync callback for all orderbook callbacks"""
            if self.loop and self.loop.is_running():
                for callback in self.callbacks.get("orderbook", []):
                    asyncio.run_coroutine_threadsafe(
                        callback(data),
                        self.loop
                    )
        
        # Subscribe using SDK
        subscription_id = self.info.subscribe(
            subscription={"type": "l2Book", "coin": coin},
            callback=combined_callback
        )
        
        self.subscriptions.append(subscription_id)
        logger.info(f"Subscribed to orderbook: {coin} (ID: {subscription_id})")
        return subscription_id
    
    async def subscribe_user_events(self, user: str):
        """
        Subscribe to user events
        
        Args:
            user: User address
        """
        # Create sync wrapper for async callbacks
        def combined_callback(data):
            """Combined sync callback for all user event callbacks"""
            if self.loop and self.loop.is_running():
                for callback in self.callbacks.get("user", []):
                    asyncio.run_coroutine_threadsafe(
                        callback(data),
                        self.loop
                    )
        
        # Subscribe using SDK
        subscription_id = self.info.subscribe(
            subscription={"type": "userEvents", "user": user},
            callback=combined_callback
        )
        
        self.subscriptions.append(subscription_id)
        logger.info(f"Subscribed to user events: {user} (ID: {subscription_id})")
        return subscription_id
    
    async def stop(self):
        """Stop WebSocket"""
        self.running = False
        self.connected = False
        
        # Unsubscribe all tracked subscriptions
        for sub_id in self.subscriptions:
            try:
                self.info.unsubscribe(sub_id)
            except Exception as e:
                logger.warning(f"Failed to unsubscribe {sub_id}: {e}")
        
        self.subscriptions.clear()
        
        logger.info("WebSocket stopped")
