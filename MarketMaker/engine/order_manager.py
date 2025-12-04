"""
Order management engine
"""
import asyncio
import time
import uuid
from typing import Dict, List, Optional
from loguru import logger

from utils.logger import get_order_logger


class OrderManager:
    """Unified order lifecycle management"""
    
    def __init__(self, adapter, config: dict):
        """
        Initialize order manager
        
        Args:
            adapter: Exchange adapter instance
            config: Configuration dict
        """
        self.adapter = adapter
        self.config = config
        
        # Symbol info
        self.symbol = config["symbol"]["name"]
        self.category = config["symbol"]["category"]
        
        # Order settings
        self.retry_attempts = config["orders"]["retry_attempts"]
        self.retry_delay_ms = config["orders"]["retry_delay_ms"] / 1000
        self.reconcile_interval = config["orders"]["reconcile_interval_sec"]
        
        # Active orders tracking
        # {client_order_id: {order_id, price, size, side, status, timestamp}}
        self.active_orders: Dict[str, dict] = {}
        
        # Order logger
        self.order_logger = get_order_logger()
        
        # Dry run mode
        self.dry_run = config["operational"].get("dry_run", False)
        
        if self.dry_run:
            logger.warning("🔶 ORDER MANAGER IN DRY RUN MODE - NO REAL ORDERS")
        
        logger.info(f"OrderManager initialized for {self.symbol}")
    
    def generate_client_order_id(self) -> str:
        """
        Generate unique client order ID
        
        Returns:
            Client order ID
        """
        return f"mm_{int(time.time()*1000)}_{uuid.uuid4().hex[:8]}"
    
    async def place_order(
        self,
        side: str,
        price: float,
        size: float,
        client_order_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Place a single order with retry
        
        Args:
            side: 'buy' or 'sell'
            price: Order price
            size: Order size
            client_order_id: Optional client order ID
            
        Returns:
            Client order ID if successful, None otherwise
        """
        if not client_order_id:
            client_order_id = self.generate_client_order_id()
        
        # Dry run mode
        if self.dry_run:
            logger.info(f"[DRY RUN] Would place: {side} {size:.4f} @ {price:.2f}")
            self.active_orders[client_order_id] = {
                "order_id": f"dry_{client_order_id}",
                "price": price,
                "size": size,
                "side": side,
                "status": "active",
                "timestamp": time.time(),
            }
            return client_order_id
        
        # Real order placement with retry
        for attempt in range(self.retry_attempts):
            try:
                response = await self.adapter.place_order(
                    side=side,
                    price=price,
                    size=size,
                    client_order_id=client_order_id
                )
                
                # Extract order ID (exchange-specific)
                result = response.get("result", response)
                order_id = result.get("orderId") or result.get("status", {}).get("resting", [{}])[0].get("oid")
                
                # Track order
                self.active_orders[client_order_id] = {
                    "order_id": order_id,
                    "price": price,
                    "size": size,
                    "side": side,
                    "status": "active",
                    "timestamp": time.time(),
                }
                
                self.order_logger.info(
                    f"ORDER PLACED | {side.upper()} {size:.4f} @ {price:.2f} "
                    f"| Order ID: {order_id} | Client ID: {client_order_id}"
                )
                
                return client_order_id
                
            except Exception as e:
                logger.error(
                    f"Failed to place order (attempt {attempt + 1}/{self.retry_attempts}): {e}"
                )
                
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay_ms * (2 ** attempt))
        
        logger.error(f"Failed to place order after {self.retry_attempts} attempts")
        return None
    
    async def cancel_order(self, client_order_id: str) -> bool:
        """
        Cancel an order
        
        Args:
            client_order_id: Client order ID
            
        Returns:
            True if successful
        """
        order = self.active_orders.get(client_order_id)
        
        if not order:
            logger.warning(f"Order {client_order_id} not found in active orders")
            return False
        
        # Dry run mode
        if self.dry_run:
            logger.info(f"[DRY RUN] Would cancel: {client_order_id}")
            self.active_orders.pop(client_order_id, None)
            return True
        
        try:
            await self.adapter.cancel_order(
                client_order_id=client_order_id,
                order_id=order.get("order_id")
            )
            
            # Remove from active orders
            self.active_orders.pop(client_order_id, None)
            
            self.order_logger.info(
                f"ORDER CANCELLED | {order['side'].upper()} @ {order['price']:.2f} "
                f"| Client ID: {client_order_id}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel order {client_order_id}: {e}")
            return False
    
    async def cancel_all_orders(self) -> int:
        """
        Cancel all active orders
        
        Returns:
            Number of orders cancelled
        """
        logger.info(f"Cancelling all {len(self.active_orders)} active orders")
        
        # Dry run mode
        if self.dry_run:
            count = len(self.active_orders)
            self.active_orders.clear()
            logger.info(f"[DRY RUN] Would cancel {count} orders")
            return count
        
        try:
            await self.adapter.cancel_all_orders()
            
            count = len(self.active_orders)
            self.active_orders.clear()
            
            self.order_logger.info(f"CANCELLED ALL ORDERS | Count: {count}")
            
            return count
            
        except Exception as e:
            logger.error(f"Failed to cancel all orders: {e}")
            return 0
    
    async def reconcile_orders(self):
        """
        Reconcile local orders with exchange
        
        Syncs active orders state with exchange reality
        """
        if self.dry_run:
            return
        
        try:
            # Get open orders from exchange
            exchange_orders = await self.adapter.get_open_orders()
            
            # Build set of exchange order IDs
            exchange_order_ids = {
                order.get("orderLinkId") for order in exchange_orders
                if order.get("orderLinkId")
            }
            
            # Find orders that are locally tracked but not on exchange
            local_only = []
            for client_id in list(self.active_orders.keys()):
                if client_id not in exchange_order_ids:
                    local_only.append(client_id)
            
            # Remove local-only orders (probably filled or cancelled)
            for client_id in local_only:
                logger.info(f"Reconciliation: removing {client_id} (not on exchange)")
                self.active_orders.pop(client_id, None)
            
            # Find exchange orders not tracked locally
            exchange_only = exchange_order_ids - set(self.active_orders.keys())
            
            # Add exchange-only orders to tracking
            for order in exchange_orders:
                client_id = order.get("orderLinkId")
                if client_id in exchange_only:
                    logger.info(f"Reconciliation: adding {client_id} from exchange")
                    self.active_orders[client_id] = {
                        "order_id": order.get("orderId"),
                        "price": float(order.get("price", 0)),
                        "size": float(order.get("qty", 0)),
                        "side": order.get("side", "").lower(),
                        "status": "active",
                        "timestamp": time.time(),
                    }
            
            logger.debug(
                f"Reconciliation complete: {len(self.active_orders)} active orders"
            )
            
        except Exception as e:
            logger.error(f"Order reconciliation failed: {e}")
    
    def handle_order_update(self, order_data: dict):
        """
        Handle order update from WebSocket
        
        Args:
            order_data: Order update data
        """
        # Handle list of orders
        if isinstance(order_data, list):
            for order in order_data:
                self._process_single_order_update(order)
        else:
            self._process_single_order_update(order_data)
    
    def _process_single_order_update(self, order: dict):
        """Process a single order update"""
        client_id = order.get("orderLinkId")
        order_status = order.get("orderStatus", "")
        
        if not client_id:
            return
        
        # Order filled
        if order_status == "Filled":
            if client_id in self.active_orders:
                order_info = self.active_orders[client_id]
                self.order_logger.info(
                    f"ORDER FILLED | {order_info['side'].upper()} "
                    f"{order_info['size']:.4f} @ {order_info['price']:.2f} "
                    f"| Client ID: {client_id}"
                )
                self.active_orders.pop(client_id, None)
        
        # Order cancelled
        elif order_status in ["Cancelled", "Rejected"]:
            if client_id in self.active_orders:
                logger.info(f"Order {order_status.lower()}: {client_id}")
                self.active_orders.pop(client_id, None)
        
        # Order partially filled
        elif order_status == "PartiallyFilled":
            if client_id in self.active_orders:
                logger.info(f"Order partially filled: {client_id}")
    
    def get_active_orders(self) -> Dict[str, dict]:
        """
        Get active orders
        
        Returns:
            Active orders dict
        """
        return self.active_orders.copy()
    
    def get_active_order_count(self) -> int:
        """Get count of active orders"""
        return len(self.active_orders)
    
    async def replace_orders(
        self,
        target_orders: List[Dict],
        current_mid_price: float
    ):
        """
        Replace current orders with target orders
        
        Args:
            target_orders: List of target orders
            current_mid_price: Current mid price
        """
        # Cancel orders not in target
        to_cancel = []
        
        for client_id, order in self.active_orders.items():
            # Check if this order is still valid
            is_valid = False
            
            for target in target_orders:
                if (target["side"] == order["side"] and
                    abs(target["price"] - order["price"]) < 0.01):
                    is_valid = True
                    break
            
            if not is_valid:
                to_cancel.append(client_id)
        
        # Cancel invalid orders
        for client_id in to_cancel:
            await self.cancel_order(client_id)
        
        # Place new orders
        for target in target_orders:
            # Check if we already have this order
            has_order = False
            
            for order in self.active_orders.values():
                if (target["side"] == order["side"] and
                    abs(target["price"] - order["price"]) < 0.01):
                    has_order = True
                    break
            
            if not has_order:
                await self.place_order(
                    side=target["side"],
                    price=target["price"],
                    size=target["size"]
                )
