"""
Bybit REST API client
"""
import asyncio
import hashlib
import hmac
import time
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode

import httpx
from loguru import logger


class BybitRestClient:
    """Async REST client for Bybit API"""
    
    # API endpoints
    MAINNET_URL = "https://api.bybit.com"
    TESTNET_URL = "https://api-testnet.bybit.com"
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        """
        Initialize REST client
        
        Args:
            api_key: Bybit API key
            api_secret: Bybit API secret
            testnet: Use testnet if True
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = self.TESTNET_URL if testnet else self.MAINNET_URL
        
        self.client = httpx.AsyncClient(
            timeout=10.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        
        # Rate limiting
        self.rate_limit_delay = 0.1  # 10 requests/second
        self.last_request_time = 0
        
        logger.info(f"Bybit REST client initialized ({'testnet' if testnet else 'mainnet'})")
    
    def _generate_signature(self, params: Dict[str, Any], timestamp: int) -> str:
        """
        Generate HMAC SHA256 signature for Bybit API
        
        Args:
            params: Request parameters
            timestamp: Request timestamp in milliseconds
            
        Returns:
            Hex signature string
        """
        # For V5 API, signature = HMAC_SHA256(timestamp + api_key + recv_window + param_str)
        recv_window = "5000"
        param_str = urlencode(sorted(params.items()))
        
        sign_str = f"{timestamp}{self.api_key}{recv_window}{param_str}"
        
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            sign_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    async def _rate_limit(self):
        """Apply rate limiting"""
        now = time.time()
        elapsed = now - self.last_request_time
        
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)
        
        self.last_request_time = time.time()
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = True,
        retry: int = 3
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Bybit API
        
        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint
            params: Request parameters
            signed: Whether request needs signature
            retry: Number of retry attempts
            
        Returns:
            Response JSON
        """
        await self._rate_limit()
        
        params = params or {}
        url = f"{self.base_url}{endpoint}"
        
        headers = {
            "Content-Type": "application/json",
        }
        
        if signed:
            timestamp = int(time.time() * 1000)
            signature = self._generate_signature(params, timestamp)
            
            headers.update({
                "X-BAPI-API-KEY": self.api_key,
                "X-BAPI-TIMESTAMP": str(timestamp),
                "X-BAPI-SIGN": signature,
                "X-BAPI-RECV-WINDOW": "5000",
            })
        
        for attempt in range(retry):
            try:
                if method == "GET":
                    response = await self.client.get(url, params=params, headers=headers)
                elif method == "POST":
                    response = await self.client.post(url, json=params, headers=headers)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                response.raise_for_status()
                data = response.json()
                
                # Check Bybit-specific error code
                if data.get("retCode") != 0:
                    error_msg = data.get("retMsg", "Unknown error")
                    logger.error(f"Bybit API error: {error_msg} (code: {data.get('retCode')})")
                    
                    # Don't retry certain errors
                    if data.get("retCode") in [10001, 10003, 10004]:  # Auth errors
                        raise Exception(f"Auth error: {error_msg}")
                    
                    raise Exception(f"Bybit error: {error_msg}")
                
                return data
                
            except httpx.HTTPStatusError as e:
                logger.warning(f"HTTP error on attempt {attempt + 1}/{retry}: {e}")
                if attempt == retry - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
            except Exception as e:
                logger.error(f"Request error on attempt {attempt + 1}/{retry}: {e}")
                if attempt == retry - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
    
    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        qty: float,
        price: Optional[float] = None,
        time_in_force: str = "GTC",
        order_link_id: Optional[str] = None,
        category: str = "linear"
    ) -> Dict[str, Any]:
        """
        Place an order
        
        Args:
            symbol: Trading symbol (e.g., ETHUSDC)
            side: Buy or Sell
            order_type: Limit or Market
            qty: Order quantity
            price: Order price (required for Limit orders)
            time_in_force: GTC, IOC, FOK
            order_link_id: Client order ID
            category: linear (perpetual), spot, option
            
        Returns:
            Order response
        """
        params = {
            "category": category,
            "symbol": symbol,
            "side": side,
            "orderType": order_type,
            "qty": str(qty),
            "timeInForce": time_in_force,
        }
        
        if price is not None:
            params["price"] = str(price)
        
        if order_link_id:
            params["orderLinkId"] = order_link_id
        
        logger.info(f"Placing order: {side} {qty} {symbol} @ {price}")
        
        response = await self._request("POST", "/v5/order/create", params)
        
        logger.info(f"Order placed: {response.get('result', {}).get('orderId')}")
        return response
    
    async def cancel_order(
        self,
        symbol: str,
        order_id: Optional[str] = None,
        order_link_id: Optional[str] = None,
        category: str = "linear"
    ) -> Dict[str, Any]:
        """
        Cancel an order
        
        Args:
            symbol: Trading symbol
            order_id: Exchange order ID
            order_link_id: Client order ID
            category: linear, spot, option
            
        Returns:
            Cancellation response
        """
        if not order_id and not order_link_id:
            raise ValueError("Either order_id or order_link_id must be provided")
        
        params = {
            "category": category,
            "symbol": symbol,
        }
        
        if order_id:
            params["orderId"] = order_id
        if order_link_id:
            params["orderLinkId"] = order_link_id
        
        logger.info(f"Cancelling order: {order_id or order_link_id}")
        
        response = await self._request("POST", "/v5/order/cancel", params)
        return response
    
    async def cancel_all_orders(
        self,
        symbol: str,
        category: str = "linear"
    ) -> Dict[str, Any]:
        """
        Cancel all orders for a symbol
        
        Args:
            symbol: Trading symbol
            category: linear, spot, option
            
        Returns:
            Cancellation response
        """
        params = {
            "category": category,
            "symbol": symbol,
        }
        
        logger.info(f"Cancelling all orders for {symbol}")
        
        response = await self._request("POST", "/v5/order/cancel-all", params)
        return response
    
    async def get_open_orders(
        self,
        symbol: Optional[str] = None,
        category: str = "linear"
    ) -> List[Dict[str, Any]]:
        """
        Get open orders
        
        Args:
            symbol: Trading symbol (optional)
            category: linear, spot, option
            
        Returns:
            List of open orders
        """
        params = {
            "category": category,
        }
        
        if symbol:
            params["symbol"] = symbol
        
        response = await self._request("GET", "/v5/order/realtime", params)
        
        return response.get("result", {}).get("list", [])
    
    async def get_position(
        self,
        symbol: str,
        category: str = "linear"
    ) -> Dict[str, Any]:
        """
        Get position info
        
        Args:
            symbol: Trading symbol
            category: linear, spot, option
            
        Returns:
            Position info
        """
        params = {
            "category": category,
            "symbol": symbol,
        }
        
        response = await self._request("GET", "/v5/position/list", params)
        
        positions = response.get("result", {}).get("list", [])
        
        # Return first position (should only be one for the symbol)
        return positions[0] if positions else {}
    
    async def get_wallet_balance(self, account_type: str = "CONTRACT") -> Dict[str, Any]:
        """
        Get wallet balance
        
        Args:
            account_type: CONTRACT, SPOT, INVESTMENT, etc.
            
        Returns:
            Balance info
        """
        params = {
            "accountType": account_type,
        }
        
        response = await self._request("GET", "/v5/account/wallet-balance", params)
        
        return response.get("result", {})
    
    async def set_leverage(
        self,
        symbol: str,
        buy_leverage: float,
        sell_leverage: float,
        category: str = "linear"
    ) -> Dict[str, Any]:
        """
        Set leverage
        
        Args:
            symbol: Trading symbol
            buy_leverage: Long leverage
            sell_leverage: Short leverage
            category: linear, spot, option
            
        Returns:
            Response
        """
        params = {
            "category": category,
            "symbol": symbol,
            "buyLeverage": str(buy_leverage),
            "sellLeverage": str(sell_leverage),
        }
        
        logger.info(f"Setting leverage for {symbol}: {buy_leverage}x")
        
        response = await self._request("POST", "/v5/position/set-leverage", params)
        return response
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
        logger.info("Bybit REST client closed")
