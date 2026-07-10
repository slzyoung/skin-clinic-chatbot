import sys
from loguru import logger

def setup_logging(log_level: str = "INFO"):
    """
    Configures standard logging across the application.
    Will log to both stdout and a file.
    """
    logger.remove() # Remove default handler
    
    # Add stdout handler
    logger.add(
        sys.stdout, 
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # Add file handler
    logger.add(
        "logs/rag_system.log", 
        level="DEBUG", # Always log debug to file
        rotation="10 MB",
        retention="10 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )
    
    logger.info("Logging configured successfully.")
