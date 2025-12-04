"""
Inventory-based position management
"""
from typing import Optional
from loguru import logger


class InventoryManager:
    """Manage position inventory and calculate skew"""
    
    def __init__(self, config: dict):
        """
        Initialize inventory manager
        
        Args:
            config: Configuration dict
        """
        self.config = config
        
        # Capital settings
        self.initial_capital = config["capital"]["initial_usdc"]
        self.leverage = config["capital"]["leverage"]
        
        # Inventory settings
        self.max_position_pct = config["inventory"]["max_position_pct"]
        self.skew_threshold_pct = config["inventory"]["skew_threshold_pct"]
        self.bias_strength = config["inventory"]["bias_strength"]
        
        # Current position
        self.position_size = 0.0  # Positive = long, negative = short
        self.entry_price = 0.0
        self.unrealized_pnl = 0.0
        
        # Max position (will be calculated based on price)
        self.max_position_size = 0.0
        
        logger.info(
            f"InventoryManager initialized: capital={self.initial_capital}, "
            f"leverage={self.leverage}x"
        )
    
    def update_max_position(self, current_price: float):
        """
        Update max position size based on current price
        
        Args:
            current_price: Current market price
        """
        # Max position = (capital * leverage * max_position_pct) / price
        max_value = self.initial_capital * self.leverage * self.max_position_pct
        self.max_position_size = max_value / current_price
        
        logger.debug(f"Max position size updated: {self.max_position_size:.4f} @ {current_price}")
    
    def update_position(
        self,
        size: float,
        entry_price: Optional[float] = None,
        current_price: Optional[float] = None
    ):
        """
        Update current position
        
        Args:
            size: Position size (positive = long, negative = short)
            entry_price: Average entry price (optional)
            current_price: Current market price for PnL calculation
        """
        self.position_size = size
        
        if entry_price is not None:
            self.entry_price = entry_price
        
        # Calculate unrealized PnL
        if current_price and self.entry_price and self.position_size != 0:
            self.unrealized_pnl = (current_price - self.entry_price) * self.position_size
        else:
            self.unrealized_pnl = 0.0
        
        logger.debug(
            f"Position updated: size={self.position_size:.4f}, "
            f"entry={self.entry_price:.2f}, uPnL={self.unrealized_pnl:.2f}"
        )
    
    def get_inventory_pct(self) -> float:
        """
        Get inventory as percentage of max position
        
        Returns:
            Inventory percentage (-100 to +100)
        """
        if self.max_position_size == 0:
            return 0.0
        
        return (self.position_size / self.max_position_size) * 100
    
    def get_inventory_skew(self) -> float:
        """
        Calculate inventory skew for grid adjustment
        
        Returns:
            Skew from -1.0 to +1.0
            Positive = long position (need to sell more)
            Negative = short position (need to buy more)
        """
        inventory_pct = self.get_inventory_pct()
        
        # If within threshold, no skew
        if abs(inventory_pct) < self.skew_threshold_pct:
            return 0.0
        
        # Calculate skew beyond threshold
        # Map threshold to max_position to 0 to 1
        if inventory_pct > 0:
            # Long position
            excess = inventory_pct - self.skew_threshold_pct
            max_excess = 100 - self.skew_threshold_pct
            skew = min(excess / max_excess, 1.0)
        else:
            # Short position
            excess = abs(inventory_pct) - self.skew_threshold_pct
            max_excess = 100 - self.skew_threshold_pct
            skew = -min(excess / max_excess, 1.0)
        
        return skew
    
    def should_trade(self, side: str) -> bool:
        """
        Check if we can trade in given direction
        
        Args:
            side: 'buy' or 'sell'
            
        Returns:
            True if can trade
        """
        if self.max_position_size == 0:
            return False
        
        if side.lower() == "buy":
            # Check if we can go more long
            return self.position_size < self.max_position_size
        else:
            # Check if we can go more short
            return self.position_size > -self.max_position_size
    
    def get_position_info(self) -> dict:
        """
        Get position information
        
        Returns:
            Position info dict
        """
        return {
            "size": self.position_size,
            "entry_price": self.entry_price,
            "unrealized_pnl": self.unrealized_pnl,
            "inventory_pct": self.get_inventory_pct(),
            "inventory_skew": self.get_inventory_skew(),
            "max_position": self.max_position_size,
        }
    
    def calculate_target_size(self, side: str) -> float:
        """
        Calculate target order size considering inventory
        
        Args:
            side: 'buy' or 'sell'
            
        Returns:
            Target order size
        """
        base_size = self.config["grid"]["order_size_usdc"]
        
        # Adjust size based on inventory skew
        skew = self.get_inventory_skew()
        
        if side.lower() == "buy":
            # Reduce buy size when long, increase when short
            adjustment = 1.0 - (skew * self.bias_strength)
        else:
            # Reduce sell size when short, increase when long
            adjustment = 1.0 + (skew * self.bias_strength)
        
        # Ensure positive and reasonable
        adjustment = max(0.5, min(adjustment, 1.5))
        
        return base_size * adjustment
