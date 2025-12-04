"""
Grid maker strategy with sliding grids
"""
from typing import List, Dict, Optional
from loguru import logger


class GridLevel:
    """Represents a single grid level"""
    
    def __init__(self, price: float, size: float, side: str):
        self.price = price
        self.size = size
        self.side = side  # 'buy' or 'sell'
    
    def __repr__(self):
        return f"GridLevel({self.side} {self.size} @ {self.price})"


class GridMaker:
    """Grid generation and management"""
    
    def __init__(self, config: dict):
        """
        Initialize grid maker
        
        Args:
            config: Configuration dict
        """
        self.config = config
        
        # Grid parameters
        self.spacing_pct = config["grid"]["spacing_pct"] / 100  # Convert to decimal
        self.num_levels = config["grid"]["num_levels"]
        self.base_order_size = config["grid"]["order_size_usdc"]
        self.slide_threshold_pct = config["grid"]["slide_threshold_pct"] / 100
        
        # Current grid state
        self.current_mid_price = 0.0
        self.grid_levels: List[GridLevel] = []
        
        logger.info(
            f"GridMaker initialized: spacing={self.spacing_pct*100:.2f}%, "
            f"levels={self.num_levels}, size={self.base_order_size}"
        )
    
    def generate_grid(
        self,
        mid_price: float,
        inventory_skew: float = 0.0,
        price_precision: int = 2
    ) -> List[GridLevel]:
        """
        Generate grid levels around mid price
        
        Args:
            mid_price: Current mid price
            inventory_skew: Inventory skew from -1 to +1
            price_precision: Price decimal places
            
        Returns:
            List of GridLevel objects
        """
        grid = []
        
        # Calculate spacing adjustment based on inventory
        # Positive skew (long) -> widen buy grid, narrow sell grid
        # Negative skew (short) -> narrow buy grid, widen sell grid
        buy_spacing = self.spacing_pct * (1 + inventory_skew * 0.5)
        sell_spacing = self.spacing_pct * (1 - inventory_skew * 0.5)
        
        # Generate buy levels (below mid)
        for i in range(1, self.num_levels + 1):
            price = mid_price * (1 - buy_spacing * i)
            price = round(price, price_precision)
            
            grid.append(GridLevel(
                price=price,
                size=self.base_order_size / price,  # Convert USD to contracts
                side="buy"
            ))
        
        # Generate sell levels (above mid)
        for i in range(1, self.num_levels + 1):
            price = mid_price * (1 + sell_spacing * i)
            price = round(price, price_precision)
            
            grid.append(GridLevel(
                price=price,
                size=self.base_order_size / price,  # Convert USD to contracts
                side="sell"
            ))
        
        self.grid_levels = grid
        self.current_mid_price = mid_price
        
        logger.debug(f"Generated grid with {len(grid)} levels around {mid_price}")
        
        return grid
    
    def should_slide_grid(self, current_mid_price: float) -> bool:
        """
        Check if grid should be re-centered
        
        Args:
            current_mid_price: Current mid price
            
        Returns:
            True if should slide
        """
        if self.current_mid_price == 0:
            return True
        
        price_change_pct = abs(
            (current_mid_price - self.current_mid_price) / self.current_mid_price
        )
        
        should_slide = price_change_pct >= self.slide_threshold_pct
        
        if should_slide:
            logger.info(
                f"Grid slide triggered: price moved {price_change_pct*100:.2f}% "
                f"(threshold {self.slide_threshold_pct*100:.2f}%)"
            )
        
        return should_slide
    
    def get_grid_by_side(self, side: str) -> List[GridLevel]:
        """
        Get grid levels for one side
        
        Args:
            side: 'buy' or 'sell'
            
        Returns:
            List of grid levels
        """
        return [level for level in self.grid_levels if level.side == side]
    
    def get_target_orders(
        self,
        mid_price: float,
        inventory_skew: float = 0.0,
        active_orders: Optional[Dict[str, dict]] = None
    ) -> List[Dict]:
        """
        Get target orders (cancellations + new orders)
        
        Args:
            mid_price: Current mid price
            inventory_skew: Inventory skew
            active_orders: Currently active orders {order_id: {price, size, side}}
            
        Returns:
            List of target orders
        """
        active_orders = active_orders or {}
        
        # Check if we should regenerate grid
        if self.should_slide_grid(mid_price):
            self.generate_grid(mid_price, inventory_skew)
        
        # Convert grid levels to target orders
        target_orders = []
        
        for level in self.grid_levels:
            # Check if we already have an order at this price
            has_order = False
            
            for order_id, order in active_orders.items():
                if (order["side"] == level.side and
                    abs(order["price"] - level.price) < 0.01):  # Small tolerance
                    has_order = True
                    break
            
            if not has_order:
                target_orders.append({
                    "side": level.side,
                    "price": level.price,
                    "size": level.size,
                })
        
        return target_orders
    
    def get_orders_to_cancel(
        self,
        active_orders: Dict[str, dict],
        mid_price: float
    ) -> List[str]:
        """
        Get orders that should be cancelled
        
        Args:
            active_orders: Active orders {order_id: {price, size, side}}
            mid_price: Current mid price
            
        Returns:
            List of order IDs to cancel
        """
        to_cancel = []
        
        # Get valid price ranges for grid
        buy_prices = {level.price for level in self.grid_levels if level.side == "buy"}
        sell_prices = {level.price for level in self.grid_levels if level.side == "sell"}
        
        for order_id, order in active_orders.items():
            should_cancel = False
            
            if order["side"] == "buy":
                # Cancel if not in current buy grid
                if not any(abs(order["price"] - p) < 0.01 for p in buy_prices):
                    should_cancel = True
            else:
                # Cancel if not in current sell grid
                if not any(abs(order["price"] - p) < 0.01 for p in sell_prices):
                    should_cancel = True
            
            if should_cancel:
                to_cancel.append(order_id)
        
        return to_cancel
    
    def get_grid_info(self) -> dict:
        """
        Get grid information
        
        Returns:
            Grid info dict
        """
        buy_levels = self.get_grid_by_side("buy")
        sell_levels = self.get_grid_by_side("sell")
        
        return {
            "mid_price": self.current_mid_price,
            "num_levels": self.num_levels,
            "spacing_pct": self.spacing_pct * 100,
            "buy_levels": len(buy_levels),
            "sell_levels": len(sell_levels),
            "lowest_buy": min([l.price for l in buy_levels]) if buy_levels else None,
            "highest_sell": max([l.price for l in sell_levels]) if sell_levels else None,
        }
