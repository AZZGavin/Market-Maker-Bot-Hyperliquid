"""
Hyperliquid REST API client using official SDK
"""
from typing import Dict, List, Optional, Any
from loguru import logger
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants


class HyperliquidClient:
    """Unified Hyperliquid client using official SDK"""
    
    def __init__(self, private_key: str, testnet: bool = True):
        """
        Initialize Hyperliquid client
        
        Args:
            private_key: Ethereum private key
            testnet: Use testnet if True
        """
        # Clean private key
        if private_key.startswith('0x'):
            private_key = private_key[2:]
        
        self.private_key = private_key
        self.testnet = testnet
        
        # Create Account object from private key
        from eth_account import Account
        self.account = Account.from_key(private_key)
        self.address = self.account.address
        
        # Set base URL
        if testnet:
            base_url = constants.TESTNET_API_URL
        else:
            base_url = constants.MAINNET_API_URL
        
        # Initialize SDK clients with Account object (not string)
        self.exchange = Exchange(
            wallet=self.account,  # Pass Account object, not string
            base_url=base_url,
            account_address=None  # Will use wallet address
        )
        
        self.info = Info(base_url=base_url, skip_ws=True)
        
        logger.info(f"Hyperliquid client initialized ({'testnet' if testnet else 'mainnet'})")
        logger.info(f"Wallet address: {self.address}")
    
    async def place_order(
        self,
        coin: str,
        is_buy: bool,
        sz: float,
        limit_px: float,
        reduce_only: bool = False
    ) -> Dict[str, Any]:
        """
        Place an order
        
        Args:
            coin: Trading pair (e.g., "ETH")
            is_buy: True for buy, False for sell
            sz: Order size
            limit_px: Limit price
            reduce_only: Reduce only flag
            
        Returns:
            Order response
        """
        # Round size to avoid precision errors
        # Hyperliquid typically requires 4 decimal places for ETH
        sz = round(sz, 4)
        limit_px = round(limit_px, 2)
        
        order_result = self.exchange.order(
            name=coin,  # SDK uses 'name' not 'coin'
            is_buy=is_buy,
            sz=sz,
            limit_px=limit_px,
            order_type={"limit": {"tif": "Gtc"}},
            reduce_only=reduce_only
        )
        
        logger.info(f"Order placed: {'BUY' if is_buy else 'SELL'} {sz} {coin} @ {limit_px}")
        return order_result
    
    async def cancel_order(self, coin: str, oid: int) -> Dict[str, Any]:
        """
        Cancel an order
        
        Args:
            coin: Trading pair
            oid: Order ID
            
        Returns:
            Cancellation response
        """
        result = self.exchange.cancel(coin=coin, oid=oid)
        logger.info(f"Order cancelled: {oid}")
        return result
    
    async def cancel_all_orders(self, coin: str) -> Dict[str, Any]:
        """
        Cancel all orders for a coin
        
        Args:
            coin: Trading pair
            
        Returns:
            Cancellation response
        """
        # Get all open orders
        open_orders = await self.get_open_orders()
        
        # Filter for this coin and prepare cancel requests
        cancel_requests = []
        for order in open_orders:
            if order.get("coin") == coin:
                cancel_requests.append({
                    "a": order.get("coin"),  # asset
                    "o": order.get("oid")    # order id
                })
        
        if not cancel_requests:
            logger.info(f"No orders to cancel for {coin}")
            return {"status": "ok", "response": {"type": "cancel", "data": {"statuses": []}}}
        
        # Use bulk_cancel
        result = self.exchange.bulk_cancel(cancel_requests)
        logger.info(f"Cancelled {len(cancel_requests)} orders for {coin}")
        return result
    
    async def get_open_orders(self, user: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get open orders
        
        Args:
            user: User address (defaults to self)
            
        Returns:
            List of open orders
        """
        user = user or self.address
        orders = self.info.open_orders(user=user)
        return orders if orders else []
    
    async def get_user_state(self, user: Optional[str] = None) -> Dict[str, Any]:
        """
        Get user state including positions and balances
        
        Args:
            user: User address (defaults to self)
            
        Returns:
            User state
        """
        address = user or self.address
        state = self.info.user_state(address=address)  # SDK uses 'address' not 'user'
        return state
    
    async def get_position(self, coin: str) -> Optional[Dict[str, Any]]:
        """
        Get position for a specific coin
        
        Args:
            coin: Trading pair
            
        Returns:
            Position data or None
        """
        state = await self.get_user_state()
        
        if not state or 'assetPositions' not in state:
            return None
        
        for pos in state['assetPositions']:
            position = pos.get('position', {})
            if position.get('coin') == coin:
                return pos
        
        return None
    
    def get_l2_snapshot(self, coin: str) -> Dict[str, Any]:
        """
        Get L2 orderbook snapshot
        
        Args:
            coin: Trading pair
            
        Returns:
            Orderbook data
        """
        return self.info.l2_snapshot(coin=coin)
    
    async def set_leverage(
        self,
        coin: str,
        leverage: int,
        is_cross: bool = True
    ) -> Dict[str, Any]:
        """
        Set leverage for a coin
        
        Args:
            coin: Trading pair
            leverage: Leverage value
            is_cross: Cross margin if True, isolated if False
            
        Returns:
            Response
        """
        result = self.exchange.update_leverage(
            leverage=leverage,
            name=coin,  # SDK uses 'name' not 'coin'
            is_cross=is_cross
        )
        
        logger.info(f"Leverage set for {coin}: {leverage}x ({'cross' if is_cross else 'isolated'})")
        return result
    
    async def close(self):
        """Close client"""
        logger.info("Hyperliquid client closed")
