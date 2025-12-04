"""
Simplified factory for Hyperliquid only
"""
from typing import Tuple, Any
from loguru import logger
from exchange.hyperliquid_client import HyperliquidClient
from exchange.hyperliquid_ws import HyperliquidWebSocket


class ExchangeFactory:
    """Factory to create Hyperliquid clients"""
    
    @staticmethod
    def create_clients(config: dict) -> Tuple[Any, Any]:
        """
        Create Hyperliquid clients
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Tuple of (rest_client, ws_client)
        """
        testnet = config["exchange"]["testnet"]
        
        logger.info("Creating Hyperliquid clients")
        
        rest_client = HyperliquidClient(
            private_key=config["exchange"]["private_key"],
            testnet=testnet
        )
        
        ws_client = HyperliquidWebSocket(
            testnet=testnet
        )
        
        return rest_client, ws_client
