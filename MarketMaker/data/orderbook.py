"""
Orderbook management and price data
"""
import asyncio
import time
from typing import Dict, List, Optional, Tuple
from loguru import logger


class OrderBook:
    """Local orderbook manager"""
    
    def __init__(self, symbol: str):
        """
        Initialize orderbook
        
        Args:
            symbol: Trading symbol
        """
        self.symbol = symbol
        
        # Orderbook data: {price: size}
        self.bids: Dict[float, float] = {}
        self.asks: Dict[float, float] = {}
        
        # Metadata
        self.last_update_time = 0
        self.update_id = 0
        
        # Lock for thread safety
        self.lock = asyncio.Lock()
        
        # Staleness detection
        self.staleness_threshold = 5.0  # seconds
        
        logger.info(f"OrderBook initialized for {symbol}")
    
    async def update_from_snapshot(self, snapshot: Dict):
        """
        Update from full snapshot
        
        Args:
            snapshot: Snapshot data from WebSocket
        """
        async with self.lock:
            try:
                # Parse bids and asks
                bids = snapshot.get("b", [])
                asks = snapshot.get("a", [])
                
                # Clear existing data
                self.bids.clear()
                self.asks.clear()
                
                # Update bids
                for bid in bids:
                    price = float(bid[0])
                    size = float(bid[1])
                    if size > 0:
                        self.bids[price] = size
                
                # Update asks
                for ask in asks:
                    price = float(ask[0])
                    size = float(ask[1])
                    if size > 0:
                        self.asks[price] = size
                
                self.last_update_time = time.time()
                self.update_id = snapshot.get("u", 0)
                
                logger.debug(
                    f"Orderbook snapshot: {len(self.bids)} bids, "
                    f"{len(self.asks)} asks"
                )
                
            except Exception as e:
                logger.error(f"Error updating orderbook from snapshot: {e}")
    
    async def update_from_delta(self, delta: Dict):
        """
        Update from delta
        
        Args:
            delta: Delta data from WebSocket
        """
        async with self.lock:
            try:
                # Parse bids and asks
                bids = delta.get("b", [])
                asks = delta.get("a", [])
                
                # Update bids
                for bid in bids:
                    price = float(bid[0])
                    size = float(bid[1])
                    
                    if size == 0:
                        # Remove price level
                        self.bids.pop(price, None)
                    else:
                        self.bids[price] = size
                
                # Update asks
                for ask in asks:
                    price = float(ask[0])
                    size = float(ask[1])
                    
                    if size == 0:
                        # Remove price level
                        self.asks.pop(price, None)
                    else:
                        self.asks[price] = size
                
                self.last_update_time = time.time()
                self.update_id = delta.get("u", self.update_id)
                
            except Exception as e:
                logger.error(f"Error updating orderbook from delta: {e}")
    
    async def handle_orderbook_message(self, data: Dict):
        """
        Handle orderbook message from WebSocket
        
        Args:
            data: Orderbook data
        """
        # Check if this is Hyperliquid format
        if "data" in data and "coin" in data.get("data", {}):
            # Hyperliquid l2Book format
            book_data = data.get("data", {})
            
            # Check if it's for our symbol
            if book_data.get("coin") != self.symbol:
                return
            
            # Hyperliquid sends full snapshot each time
            await self._update_from_hyperliquid(book_data)
        else:
            # Bybit format
            msg_type = data.get("type", "")
            
            if msg_type == "snapshot":
                await self.update_from_snapshot(data)
            elif msg_type == "delta":
                await self.update_from_delta(data)
    
    async def _update_from_hyperliquid(self, book_data: Dict):
        """
        Update from Hyperliquid l2Book data
        
        Args:
            book_data: Hyperliquid book data
        """
        async with self.lock:
            try:
                # Hyperliquid format: {"coin": "ETH", "levels": [[price, size, side], ...], "time": ...}
                levels = book_data.get("levels", [])
                
                # Clear existing data
                self.bids.clear()
                self.asks.clear()
                
                # Process levels
                # In Hyperliquid, levels is [[bid_levels], [ask_levels]]
                if len(levels) >= 2:
                    bid_levels = levels[0] if isinstance(levels[0], list) else []
                    ask_levels = levels[1] if isinstance(levels[1], list) and len(levels) > 1 else []
                    
                    # Update bids
                    for bid in bid_levels:
                        if isinstance(bid, dict):
                            price = float(bid.get("px", 0))
                            size = float(bid.get("sz", 0))
                            if size > 0:
                                self.bids[price] = size
                    
                    # Update asks
                    for ask in ask_levels:
                        if isinstance(ask, dict):
                            price = float(ask.get("px", 0))
                            size = float(ask.get("sz", 0))
                            if size > 0:
                                self.asks[price] = size
                
                self.last_update_time = time.time()
                
                logger.debug(
                    f"Hyperliquid orderbook: {len(self.bids)} bids, {len(self.asks)} asks"
                )
                
            except Exception as e:
                logger.error(f"Error updating orderbook from Hyperliquid: {e}", exc_info=True)
    
    def get_best_bid(self) -> Optional[Tuple[float, float]]:
        """
        Get best bid (highest price)
        
        Returns:
            (price, size) tuple or None
        """
        if not self.bids:
            return None
        
        best_price = max(self.bids.keys())
        return (best_price, self.bids[best_price])
    
    def get_best_ask(self) -> Optional[Tuple[float, float]]:
        """
        Get best ask (lowest price)
        
        Returns:
            (price, size) tuple or None
        """
        if not self.asks:
            return None
        
        best_price = min(self.asks.keys())
        return (best_price, self.asks[best_price])
    
    def get_mid_price(self) -> Optional[float]:
        """
        Get mid price
        
        Returns:
            Mid price or None
        """
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        
        if not best_bid or not best_ask:
            return None
        
        return (best_bid[0] + best_ask[0]) / 2.0
    
    def get_spread(self) -> Optional[float]:
        """
        Get bid-ask spread
        
        Returns:
            Spread or None
        """
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        
        if not best_bid or not best_ask:
            return None
        
        return best_ask[0] - best_bid[0]
    
    def get_spread_bps(self) -> Optional[float]:
        """
        Get spread in basis points
        
        Returns:
            Spread in bps or None
        """
        spread = self.get_spread()
        mid = self.get_mid_price()
        
        if not spread or not mid:
            return None
        
        return (spread / mid) * 10000
    
    def get_price_at_depth(self, side: str, depth_usd: float) -> Optional[float]:
        """
        Get price after consuming depth
        
        Args:
            side: 'buy' or 'sell'
            depth_usd: Depth in USD to consume
            
        Returns:
            Price or None
        """
        if side == "buy":
            # Buying = consuming asks
            levels = sorted(self.asks.items(), key=lambda x: x[0])
        else:
            # Selling = consuming bids
            levels = sorted(self.bids.items(), key=lambda x: x[0], reverse=True)
        
        cumulative = 0
        
        for price, size in levels:
            value = price * size
            cumulative += value
            
            if cumulative >= depth_usd:
                return price
        
        return None
    
    def is_stale(self) -> bool:
        """
        Check if orderbook is stale
        
        Returns:
            True if stale
        """
        if self.last_update_time == 0:
            return True
        
        elapsed = time.time() - self.last_update_time
        return elapsed > self.staleness_threshold
    
    def get_top_levels(self, n: int = 5) -> Dict[str, List[Tuple[float, float]]]:
        """
        Get top N levels
        
        Args:
            n: Number of levels
            
        Returns:
            Dict with 'bids' and 'asks' lists
        """
        sorted_bids = sorted(self.bids.items(), key=lambda x: x[0], reverse=True)[:n]
        sorted_asks = sorted(self.asks.items(), key=lambda x: x[0])[:n]
        
        return {
            "bids": sorted_bids,
            "asks": sorted_asks
        }
    
    def __repr__(self) -> str:
        """String representation"""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        mid = self.get_mid_price()
        
        return (
            f"OrderBook({self.symbol}): "
            f"bid={best_bid[0] if best_bid else None}, "
            f"ask={best_ask[0] if best_ask else None}, "
            f"mid={mid:.2f if mid else None}"
        )
