"""
Structured logging setup using loguru
"""
import sys
from pathlib import Path
from loguru import logger


def setup_logger(config: dict) -> None:
    """
    Configure loguru logger based on config
    
    Args:
        config: Logging configuration dict
    """
    log_config = config.get("logging", {})
    
    # Remove default handler
    logger.remove()
    
    # Console handler
    if log_config.get("console", True):
        logger.add(
            sys.stdout,
            level=log_config.get("level", "INFO"),
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                   "<level>{level: <8}</level> | "
                   "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                   "<level>{message}</level>",
            colorize=True,
        )
    
    # File handler
    if log_config.get("file", True):
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # General log
        logger.add(
            log_dir / "market_maker.log",
            level=log_config.get("level", "INFO"),
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
            rotation=log_config.get("rotation", "50 MB"),
            retention=log_config.get("retention", "7 days"),
            compression="zip",
        )
        
        # Trade log (always INFO level)
        logger.add(
            log_dir / "trades.log",
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {message}",
            rotation=log_config.get("rotation", "50 MB"),
            retention=log_config.get("retention", "7 days"),
            filter=lambda record: "TRADE" in record["extra"],
            compression="zip",
        )
        
        # Order log
        logger.add(
            log_dir / "orders.log",
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {message}",
            rotation=log_config.get("rotation", "50 MB"),
            retention=log_config.get("retention", "7 days"),
            filter=lambda record: "ORDER" in record["extra"],
            compression="zip",
        )
        
        # Error log (errors only)
        logger.add(
            log_dir / "errors.log",
            level="ERROR",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
            rotation=log_config.get("rotation", "50 MB"),
            retention=log_config.get("retention", "30 days"),
            compression="zip",
        )


def get_logger(name: str):
    """Get a logger instance with a specific name"""
    return logger.bind(name=name)


# Specialized loggers
def get_trade_logger():
    """Logger for trade events"""
    return logger.bind(TRADE=True)


def get_order_logger():
    """Logger for order events"""
    return logger.bind(ORDER=True)
