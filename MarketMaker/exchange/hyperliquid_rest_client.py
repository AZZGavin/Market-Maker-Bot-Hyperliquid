"""
Hyperliquid REST API client
"""
import asyncio
import time
from typing import Dict, List, Optional, Any
from eth_account import Account
from eth_account.signers.local import LocalAccount
import json

import httpx
from loguru import logger


class HyperliquidRestClient:
    """Async REST client for Hyperliquid API"""
    
    # API endpoints
    MAINNET_URL = "https://api.hyperliquid.xyz"
    TESTNET_URL = "https://api.hyperliquid-testnet.xyz"
    
    def __init__(self, private_key: str, testnet: bool = True):
        """
        Initialize REST client
        
        Args:
            private_key: Ethereum private key (with or without 0x prefix)
            testnet: Use testnet if True
        """
        # Clean private key
        if private_key.startswith('0x'):
            private_key = private_key[2:]
        
        self.private_key = private_key
        self.account: LocalAccount = Account.from_key(private_key)
        self.address = self.account.address
        self.testnet = testnet
        self.base_url = self.TESTNET_URL if testnet else self.MAINNET_URL
        
        self.client = httpx.AsyncClient(
            timeout=10.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        
        # Rate limiting
        self.rate_limit_delay = 0.1
        self.last_request_time = 0
        
        logger.info(f"Hyperliquid REST client initialized ({'testnet' if testnet else 'mainnet'})")
        logger.info(f"Wallet address: {self.address}")
    
    async def _rate_limit(self):
        """Apply rate limiting"""
        now = time.time()
        elapsed = now - self.last_request_time
        
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)
        
        self.last_request_time = time.time()
    
    def _sign_l1_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sign an L1 action for Hyperliquid
        
        Args:
            action: Action to sign
            
        Returns:
            Signed action with signature
        """
        # Hyperliquid uses EIP-712 structured data signing
        # For now, use a simplified signing approach
        import hashlib
        
        message = json.dumps(action, separators=(',', ':'))
        message_bytes = message.encode('utf-8')
        
        # Create message hash
        message_hash = hashlib.sha256(message_bytes).digest()
        
        # Sign the hash
        signature = self.account.signHash(message_hash)
        
        return {
            "action": action,
            "nonce": int(time.time() * 1000),
            "signature": {
                "r": hex(signature.r),
                "s": hex(signature.s),
                "v": signature.v
            },
            "vaultAddress": None
        }
    
    async def _request(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        retry: int = 3
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Hyperliquid API
        
        Args:
            endpoint: API endpoint
            data: Request data
            retry: Number of retry attempts
            
        Returns:
            Response JSON
        """
        await self._rate_limit()
        
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(retry):
            try:
                response = await self.client.post(url, json=data)
                response.raise_for_status()
                result = response.json()
                
                return result
                
            except httpx.HTTPStatusError as e:
                logger.warning(f"HTTP error on attempt {attempt + 1}/{retry}: {e}")
                if attempt == retry - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
                
            except Exception as e:
                logger.error(f"Request error on attempt {attempt + 1}/{retry}: {e}")
                if attempt == retry - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
    
    async def place_order(
        self,
        coin: str,
        is_buy: bool,
        sz: float,
        limit_px: float,
        order_type: Dict[str, Any] = {"limit": {"tif": "Gtc"}},
        reduce_only: bool = False
    ) -> Dict[str, Any]:
        """
        Place an order
        
        Args:
            coin: Trading pair (e.g., "ETH")
            is_buy: True for buy, False for sell
            sz: Order size
            limit_px: Limit price
            order_type: Order type specification
            reduce_only: Reduce only flag
            
        Returns:
            Order response
        """
        action = {
            "type": "order",
            "orders": [{
                "a": self.address,
                "b": is_buy,
                "p": str(limit_px),
                "s": str(sz),
                "r": reduce_only,
                "t": order_type
            }],
            "grouping": "na"
        }
        
        signed_action = self._sign_l1_action(action)
        
        logger.info(f"Placing order: {'BUY' if is_buy else 'SELL'} {sz} {coin} @ {limit_px}")
        
        response = await self._request("/exchange", signed_action)
        
        logger.info(f"Order placed: {response}")
        return response
    
    async def cancel_order(self, coin: str, oid: int) -> Dict[str, Any]:
        """
        Cancel an order
        
        Args:
            coin: Trading pair
            oid: Order ID
            
        Returns:
            Cancellation response
        """
        action = {
            "type": "cancel",
            "cancels": [{
                "a": self.address,
                "o": oid
            }]
        }
        
        signed_action = self._sign_l1_action(action)
        
        logger.info(f"Cancelling order: {oid}")
        
        response = await self._request("/exchange", signed_action)
        return response
    
    async def cancel_all_orders(self, coin: str) -> Dict[str, Any]:
        """
        Cancel all orders for a coin
        
        Args:
            coin: Trading pair
            
        Returns:
            Cancellation response
        """
        action = {
            "type": "cancelByCloid",
            "cancels": [{
                "asset": coin,
                "cloid": None  # None cancels all
            }]
        }
        
        signed_action = self._sign_l1_action(action)
        
        logger.info(f"Cancelling all orders for {coin}")
        
        response = await self._request("/exchange", signed_action)
        return response
    
    async def get_open_orders(self, user: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get open orders
        
        Args:
            user: User address (defaults to self)
            
        Returns:
            List of open orders
        """
        data = {
            "type": "openOrders",
            "user": user or self.address
        }
        
        response = await self._request("/info", data)
        return response if isinstance(response, list) else []
    
    async def get_user_state(self, user: Optional[str] = None) -> Dict[str, Any]:
        """
        Get user state including positions and balances
        
        Args:
            user: User address (defaults to self)
            
        Returns:
            User state
        """
        data = {
            "type": "clearinghouseState",
            "user": user or self.address
        }
        
        response = await self._request("/info", data)
        return response
    
    async def get_meta(self) -> Dict[str, Any]:
        """
        Get exchange metadata
        
        Returns:
            Exchange metadata
        """
        data = {"type": "meta"}
        response = await self._request("/info", data)
        return response
    
    async def set_leverage(self, coin: str, leverage: int, is_cross: bool = True) -> Dict[str, Any]:
        """
        Set leverage for a coin
        
        Args:
            coin: Trading pair
            leverage: Leverage value
            is_cross: Cross margin if True, isolated if False
            
        Returns:
            Response
        """
        action = {
            "type": "updateLeverage",
            "asset": coin,
            "isCross": is_cross,
            "leverage": leverage
        }
        
        signed_action = self._sign_l1_action(action)
        
        logger.info(f"Setting leverage for {coin}: {leverage}x ({'cross' if is_cross else 'isolated'})")
        
        response = await self._request("/exchange", signed_action)
        return response
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
        logger.info("Hyperliquid REST client closed")
