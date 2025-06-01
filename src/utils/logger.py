import logging
from src.utils import config

# _loggers = {}  # Keep track of loggers to shut them down later

def setup_logger(module_name: str):
    """Set up a logger for the given module name."""
    # if module_name in _loggers:
    #     return _loggers[module_name]

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

#     _loggers[module_name] = logger
    return logger

# def shutdown():
#     """Shutdown all loggers and remove handlers."""
#     for name, logger in _loggers.items():
#         for handler in logger.handlers[:]:
#             handler.close()
#             logger.removeHandler(handler)
