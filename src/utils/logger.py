import logging
from src.utils import config

def setup_logger(module_name: str):
    """ Set up a logger for the given module name. """
    logger = logging.getLogger(module_name)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG if config.DEBUG else logging.INFO)

        handler = logging.StreamHandler()
        handler.setFormatter(
            # logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )

        logger.addHandler(handler)
        logger.propagate = False  # prevents duplicate logs in some cases

    return logger