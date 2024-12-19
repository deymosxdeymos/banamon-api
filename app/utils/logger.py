import logging
import sys

def setup_logger():
    # Configure logger
    logger = logging.getLogger('banana_disease_api')
    logger.setLevel(logging.DEBUG)  # Set to DEBUG for more detailed logs

    # Create console handler with formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)

    # Add file handler for persistent logs
    file_handler = logging.FileHandler('banana_disease_api.log')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

# Create and configure logger
logger = setup_logger()
