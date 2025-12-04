"""
Market Maker Main Application
"""
import asyncio
import argparse
import signal
import sys
from pathlib import Path

import yaml
from loguru import logger

from utils.logger import setup_logger, get_trade_logger
from utils.persistence import StatePersistence
from exchange.factory import ExchangeFactory
from exchange.adapter import ExchangeAdapter
from data.orderbook import OrderBook
from strategy.inventory import InventoryManager
from strategy.grid_maker import GridMaker
from risk.risk_manager import RiskManager
from engine.order_manager import OrderManager


class MarketMaker:
    """Main market maker application"""
    
    def __init__(self, config_path: str = "config/config.yaml", mode: str = None):
        """
        Initialize market maker
        
        Args:
            config_path: Path to configuration file
            mode: Operating mode ('dry-run', 'testnet', 'mainnet')
        """
        # Load config
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Override config based on mode
        if mode:
            if mode == 'dry-run':
                self.config['operational']['dry_run'] = True
                self.config['exchange']['testnet'] = True
                logger.info("🔶 Mode: DRY RUN (Testnet data, no real orders)")
            elif mode == 'testnet':
                self.config['operational']['dry_run'] = False
                self.config['exchange']['testnet'] = True
                logger.info("🟡 Mode: TESTNET (Virtual funds, real orders)")
            elif mode == 'mainnet':
                self.config['operational']['dry_run'] = False
                self.config['exchange']['testnet'] = False
                logger.warning("🔴 Mode: MAINNET (REAL FUNDS, REAL ORDERS)")
        
        # Setup logging
        setup_logger(self.config)
        
        logger.info("=" * 60)
        logger.info("🚀 Market Maker Starting")
        logger.info("=" * 60)
        
        # Exchange clients
        self.rest_client = None
        self.ws_client = None
        
        # Components
        self.orderbook = None
        self.inventory_manager = None
        self.grid_maker = None
        self.risk_manager = None
        self.order_manager = None
        
        # State persistence
        self.persistence = None
        
        # Control flow
        self.running = False
        self.shutdown_event = asyncio.Event()
        
        # Symbol info
        self.symbol = self.config["symbol"]["name"]
        
        # Loggers
        self.trade_logger = get_trade_logger()
        
        # Settings
        self.loop_interval = self.config["operational"]["main_loop_interval_sec"]
        self.startup_delay = self.config["operational"]["startup_delay_sec"]
        
    async def initialize(self):
        """Initialize all components"""
        logger.info("Initializing components...")
        
        # Create exchange clients using factory
        self.rest_client, self.ws_client = ExchangeFactory.create_clients(self.config)
        
        # Create exchange adapter
        exchange_name = self.config["exchange"]["name"]
        self.adapter = ExchangeAdapter(
            exchange_name=exchange_name,
            rest_client=self.rest_client,
            symbol=self.symbol,
            category=self.config["symbol"].get("category", "linear")
        )
        
        # Data
        self.orderbook = OrderBook(self.symbol)
        
        # Strategy
        self.inventory_manager = InventoryManager(self.config)
        self.grid_maker = GridMaker(self.config)
        
        # Risk
        self.risk_manager = RiskManager(self.config)
        
        # Order management - pass adapter instead of rest_client
        self.order_manager = OrderManager(self.adapter, self.config)
        
        # State persistence
        if self.config["persistence"]["enabled"]:
            self.persistence = StatePersistence(
                self.config["persistence"]["state_file"]
            )
            self._load_state()
        
        # Set leverage using adapter
        leverage = self.config["capital"]["leverage"]
        
        try:
            await self.adapter.set_leverage(leverage)
            logger.info(f"Leverage set to {leverage}x")
        except Exception as e:
            logger.warning(f"Failed to set leverage: {e}")
        
        logger.info("✅ All components initialized")
    
    def _load_state(self):
        """Load saved state"""
        if not self.persistence:
            return
        
        state = self.persistence.load_state()
        
        if state:
            logger.info("Loaded previous state")
            # Could restore position, PnL, etc. here if needed
    
    def _save_state(self):
        """Save current state"""
        if not self.persistence:
            return
        
        state = {
            "timestamp": asyncio.get_event_loop().time(),
            "position": self.inventory_manager.get_position_info(),
            "risk": self.risk_manager.get_risk_metrics(),
            "active_orders": len(self.order_manager.active_orders),
        }
        
        self.persistence.save_state(state)
    
    async def setup_websocket(self):
        """Setup WebSocket subscriptions"""
        logger.info("Setting up WebSocket connections...")
        
        # Register callbacks
        self.ws_client.on("orderbook", self.orderbook.handle_orderbook_message)
        self.ws_client.on("user", self._handle_user_event)
        
        # Start WebSocket
        await self.ws_client.start()
        
        # Subscribe to topics
        await asyncio.sleep(2)  # Wait for connection
        
        await self.ws_client.subscribe_orderbook(self.symbol)
        await self.ws_client.subscribe_user_events(self.rest_client.address)
        
        logger.info("✅ WebSocket subscriptions active")
       
    async def _handle_user_event(self, event_data: dict):
        """
        Handle user events from Hyperliquid
        
        Args:
            event_data: User event data (fills, orders, positions)
        """
        # Handle fills
        if 'fills' in event_data:
            for fill in event_data['fills']:
                self._log_fill(fill)
        
        # Handle order updates
        if 'orders' in event_data:
            for order in event_data['orders']:
                self.order_manager.handle_order_update(order)
        
        # Handle position updates  
        if 'positions' in event_data:
            for pos in event_data['positions']:
                self._process_position(pos)
    
    def _process_position(self, pos: dict):
        """Process position update"""
        # Extract position data from Hyperliquid format
        coin = pos.get('coin')
        if coin != self.symbol:
            return
        
        szi = float(pos.get('szi', 0))  # Signed size
        entry_px = float(pos.get('entryPx', 0))
        
        self.inventory_manager.update_position(
            size=szi,
            entry_price=entry_px if entry_px > 0 else None
        )
        
        logger.debug(f"Position updated: {szi:.4f} @ {entry_px:.2f}")
    
    def _log_fill(self, fill_data: dict):
        """Log trade fill"""
        coin = fill_data.get('coin')
        if coin != self.symbol:
            return
        
        side = 'BUY' if fill_data.get('side') == 'B' else 'SELL'
        px = float(fill_data.get('px', 0))
        sz = float(fill_data.get('sz', 0))
        fee = float(fill_data.get('fee', 0))
        
        self.trade_logger.info(
            f"FILL | {side} {sz:.4f} @ {px:.2f} | Fee: {fee:.4f} USDC"
        )
    
    async def update_position_from_exchange(self):
        """Fetch position from exchange"""
        try:
            position = await self.rest_client.get_position(self.symbol)
            
            if position:
                size = float(position.get("size", 0))
                side = position.get("side", "")
                
                if side == "Sell":
                    size = -size
                
                entry_price = float(position.get("avgPrice", 0))
                unrealized_pnl = float(position.get("unrealisedPnl", 0))
                
                # Get current price
                mid_price = self.orderbook.get_mid_price()
                
                self.inventory_manager.update_position(
                    size=size,
                    entry_price=entry_price if entry_price > 0 else None,
                    current_price=mid_price
                )
                
                # Update risk manager
                self.risk_manager.update_pnl(
                    unrealized_pnl=unrealized_pnl
                )
                
        except Exception as e:
            logger.error(f"Failed to update position: {e}")
    
    async def main_loop(self):
        """Main trading loop"""
        logger.info("Starting main trading loop...")
        
        # Startup delay to let orderbook populate
        await asyncio.sleep(self.startup_delay)
        
        reconcile_counter = 0
        save_counter = 0
        
        while self.running:
            try:
                # Check if orderbook is ready
                mid_price = self.orderbook.get_mid_price()
                
                if not mid_price or self.orderbook.is_stale():
                    logger.warning("Orderbook not ready, waiting...")
                    await asyncio.sleep(self.loop_interval)
                    continue
                
                # Update position periodically
                if reconcile_counter % 10 == 0:
                    await self.update_position_from_exchange()
                
                # Update max position based on price
                self.inventory_manager.update_max_position(mid_price)
                
                # Check risk limits
                position_size = abs(self.inventory_manager.position_size)
                position_value = position_size * mid_price
                
                if self.risk_manager.check_all_limits(position_size, position_value):
                    logger.critical("🛑 Risk limits breached - stopping trading")
                    await self.order_manager.cancel_all_orders()
                    break
                
                # Get inventory skew
                inventory_skew = self.inventory_manager.get_inventory_skew()
                
                # Generate target grid
                target_orders = self.grid_maker.get_target_orders(
                    mid_price=mid_price,
                    inventory_skew=inventory_skew,
                    active_orders=self.order_manager.get_active_orders()
                )
                
                # Replace orders
                await self.order_manager.replace_orders(target_orders, mid_price)
                
                # Periodic reconciliation
                reconcile_counter += 1
                if reconcile_counter >= self.config["orders"]["reconcile_interval_sec"]:
                    await self.order_manager.reconcile_orders()
                    reconcile_counter = 0
                
                # Periodic state save
                save_counter += 1
                if save_counter >= self.config["persistence"]["save_interval_sec"]:
                    self._save_state()
                    save_counter = 0
                
                # Log status
                if reconcile_counter % 10 == 0:
                    self._log_status(mid_price)
                
                # Sleep
                await asyncio.sleep(self.loop_interval)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                await asyncio.sleep(self.loop_interval)
        
        logger.info("Main loop stopped")
    
    def _log_status(self, mid_price: float):
        """Log current status"""
        pos_info = self.inventory_manager.get_position_info()
        risk_info = self.risk_manager.get_risk_metrics()
        grid_info = self.grid_maker.get_grid_info()
        
        logger.info(
            f"📊 Status | Mid: {mid_price:.2f} | "
            f"Pos: {pos_info['size']:.4f} ({pos_info['inventory_pct']:.1f}%) | "
            f"Skew: {pos_info['inventory_skew']:.2f} | "
            f"PnL: {risk_info['total_pnl']:.2f} USDC ({risk_info['pnl_pct']:.2f}%) | "
            f"Orders: {self.order_manager.get_active_order_count()}"
        )
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("🛑 Shutting down...")
        
        self.running = False
        
        # Cancel all orders
        if self.order_manager:
            await self.order_manager.cancel_all_orders()
        
        # Save state
        self._save_state()
        
        # Close WebSocket
        if self.ws_client:
            await self.ws_client.stop()
        
        # Close REST client
        if self.rest_client:
            await self.rest_client.close()
        
        logger.info("✅ Shutdown complete")
    
    def _signal_handler(self, sig, frame):
        """Handle interrupt signals"""
        logger.warning(f"Received signal {sig}, initiating shutdown...")
        self.shutdown_event.set()
    
    async def run(self):
        """Run the market maker"""
        try:
            # Initialize
            await self.initialize()
            
            # Setup WebSocket
            await self.setup_websocket()
            
            # Start main loop
            self.running = True
            
            # Run main loop with shutdown event
            main_task = asyncio.create_task(self.main_loop())
            shutdown_task = asyncio.create_task(self.shutdown_event.wait())
            
            await asyncio.wait(
                [main_task, shutdown_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
        
        finally:
            await self.shutdown()


async def main():
    """Entry point"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Market Maker Bot',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run mode (testnet data, no real orders)
  python main.py --mode dry-run
  
  # Testnet mode (virtual funds, real orders)
  python main.py --mode testnet
  
  # Mainnet mode (REAL FUNDS!)
  python main.py --mode mainnet
  
  # Use specific config file
  python main.py --config config/config.hyperliquid.yaml --mode testnet
        """
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config/config.yaml',
        help='Path to configuration file (default: config/config.yaml)'
    )
    
    parser.add_argument(
        '--mode',
        type=str,
        choices=['dry-run', 'testnet', 'mainnet'],
        help='Operating mode: dry-run (simulate), testnet (virtual funds), mainnet (real funds)'
    )
    
    args = parser.parse_args()
    
    # Validate config file exists
    if not Path(args.config).exists():
        logger.error(f"Config file not found: {args.config}")
        sys.exit(1)
    
    # Create market maker
    mm = MarketMaker(args.config, mode=args.mode)
    
    # Setup signal handlers
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(
            sig,
            lambda: mm.shutdown_event.set()
        )
    
    # Run
    await mm.run()


if __name__ == "__main__":
    asyncio.run(main())
