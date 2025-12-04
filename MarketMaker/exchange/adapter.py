"""
Simplified adapter for Hyperliquid
"""
from typing import Dict, Any, Optional, List


class ExchangeAdapter:
    """Adapter for Hyperliquid API"""
    
    def __init__(self, rest_client, symbol: str, **kwargs):
        """
        Initialize adapter
        
        Args:
            rest_client: Hyperliquid client instance
            symbol: Trading symbol
        """
        self.rest_client = rest_client
        self.symbol = symbol
    
    async def place_order(
        self,
        side: str,
        price: float,
        size: float,
        client_order_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Place an order"""
        is_buy = side.lower() == "buy"
        return await self.rest_client.place_order(
            coin=self.symbol,
            is_buy=is_buy,
            sz=size,
            limit_px=price
        )
    
    async def cancel_order(
        self,
        client_order_id: Optional[str] = None,
        order_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Cancel an order"""
        if not order_id:
            raise ValueError("Hyperliquid requires order_id to cancel")
        return await self.rest_client.cancel_order(
            coin=self.symbol,
            oid=order_id
        )
    
    async def cancel_all_orders(self) -> Dict[str, Any]:
        """Cancel all orders"""
        return await self.rest_client.cancel_all_orders(coin=self.symbol)
    
    async def get_open_orders(self) -> List[Dict[str, Any]]:
        """Get open orders"""
        return await self.rest_client.get_open_orders()
    
    async def get_position(self) -> Optional[Dict[str, Any]]:
        """Get position"""
        return await self.rest_client.get_position(self.symbol)
    
    async def set_leverage(self, leverage: int) -> Dict[str, Any]:
        """Set leverage"""
        return await self.rest_client.set_leverage(
            coin=self.symbol,
            leverage=leverage,
            is_cross=True
        )
