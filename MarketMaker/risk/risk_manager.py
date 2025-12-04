"""
Risk management and position limits
"""
from typing import Optional
from loguru import logger


class RiskManager:
    """Monitor and enforce risk limits"""
    
    def __init__(self, config: dict):
        """
        Initialize risk manager
        
        Args:
            config: Configuration dict
        """
        self.config = config
        
        # Capital
        self.initial_capital = config["capital"]["initial_usdc"]
        self.current_capital = self.initial_capital
        
        # Risk limits
        self.max_loss_pct = config["risk"]["max_loss_pct"] / 100
        self.max_leverage = config["risk"]["max_leverage"]
        self.max_position_size = config["risk"].get("max_position_size_eth", 100.0)
        
        # PnL tracking
        self.total_realized_pnl = 0.0
        self.total_unrealized_pnl = 0.0
        self.total_fees = 0.0
        
        # Risk state
        self.emergency_stop = False
        self.stop_reason = ""
        
        logger.info(
            f"RiskManager initialized: max_loss={self.max_loss_pct*100}%, "
            f"max_leverage={self.max_leverage}x"
        )
    
    def update_pnl(
        self,
        realized_pnl: float = 0.0,
        unrealized_pnl: float = 0.0,
        fees: float = 0.0
    ):
        """
        Update PnL tracking
        
        Args:
            realized_pnl: Realized PnL from closed positions
            unrealized_pnl: Unrealized PnL from open positions
            fees: Trading fees
        """
        self.total_realized_pnl = realized_pnl
        self.total_unrealized_pnl = unrealized_pnl
        self.total_fees = fees
        
        # Update current capital
        self.current_capital = self.initial_capital + self.total_realized_pnl - self.total_fees
    
    def get_total_pnl(self) -> float:
        """
        Get total PnL (realized + unrealized - fees)
        
        Returns:
            Total PnL
        """
        return self.total_realized_pnl + self.total_unrealized_pnl - self.total_fees
    
    def get_pnl_pct(self) -> float:
        """
        Get PnL as percentage of initial capital
        
        Returns:
            PnL percentage
        """
        return (self.get_total_pnl() / self.initial_capital) * 100
    
    def check_loss_limit(self) -> bool:
        """
        Check if loss limit is breached
        
        Returns:
            True if limit breached
        """
        pnl = self.get_total_pnl()
        max_loss = self.initial_capital * self.max_loss_pct
        
        if pnl < -max_loss:
            logger.error(
                f"LOSS LIMIT BREACHED: PnL={pnl:.2f} USDC, "
                f"limit={-max_loss:.2f} USDC"
            )
            return True
        
        return False
    
    def check_leverage(self, position_value: float) -> bool:
        """
        Check if leverage is within limits
        
        Args:
            position_value: Current position value in USDC
            
        Returns:
            True if leverage exceeded
        """
        if self.current_capital <= 0:
            logger.error("Capital depleted!")
            return True
        
        current_leverage = position_value / self.current_capital
        
        if current_leverage > self.max_leverage:
            logger.error(
                f"LEVERAGE LIMIT BREACHED: {current_leverage:.2f}x > "
                f"{self.max_leverage}x"
            )
            return True
        
        return False
    
    def check_position_size(self, position_size: float) -> bool:
        """
        Check if position size is within limits
        
        Args:
            position_size: Absolute position size
            
        Returns:
            True if limit breached
        """
        abs_size = abs(position_size)
        
        if abs_size > self.max_position_size:
            logger.error(
                f"POSITION SIZE LIMIT BREACHED: {abs_size:.4f} > "
                f"{self.max_position_size:.4f}"
            )
            return True
        
        return False
    
    def check_all_limits(
        self,
        position_size: float,
        position_value: float
    ) -> bool:
        """
        Check all risk limits
        
        Args:
            position_size: Current position size
            position_value: Current position value in USDC
            
        Returns:
            True if any limit breached (should stop trading)
        """
        # Check loss limit
        if self.check_loss_limit():
            self.trigger_emergency_stop("Max loss limit breached")
            return True
        
        # Check leverage
        if self.check_leverage(position_value):
            self.trigger_emergency_stop("Max leverage exceeded")
            return True
        
        # Check position size
        if self.check_position_size(position_size):
            self.trigger_emergency_stop("Max position size exceeded")
            return True
        
        return False
    
    def trigger_emergency_stop(self, reason: str):
        """
        Trigger emergency stop
        
        Args:
            reason: Reason for stop
        """
        self.emergency_stop = True
        self.stop_reason = reason
        
        logger.critical(f"🚨 EMERGENCY STOP TRIGGERED: {reason}")
    
    def is_stopped(self) -> bool:
        """
        Check if emergency stop is active
        
        Returns:
            True if stopped
        """
        return self.emergency_stop
    
    def reset_stop(self):
        """Reset emergency stop (use with caution!)"""
        self.emergency_stop = False
        self.stop_reason = ""
        logger.warning("Emergency stop RESET")
    
    def get_risk_metrics(self) -> dict:
        """
        Get risk metrics
        
        Returns:
            Risk metrics dict
        """
        return {
            "initial_capital": self.initial_capital,
            "current_capital": self.current_capital,
            "total_pnl": self.get_total_pnl(),
            "pnl_pct": self.get_pnl_pct(),
            "realized_pnl": self.total_realized_pnl,
            "unrealized_pnl": self.total_unrealized_pnl,
            "total_fees": self.total_fees,
            "emergency_stop": self.emergency_stop,
            "stop_reason": self.stop_reason,
        }
    
    def should_reduce_risk(self) -> bool:
        """
        Check if should reduce risk exposure
        
        Returns:
            True if approaching risk limits
        """
        # Warn if PnL approaching loss limit
        pnl_pct = self.get_pnl_pct()
        warning_threshold = self.max_loss_pct * 0.75 * 100  # 75% of limit
        
        if pnl_pct < -warning_threshold:
            logger.warning(
                f"Approaching loss limit: {pnl_pct:.2f}% "
                f"(limit: {-self.max_loss_pct*100}%)"
            )
            return True
        
        return False
