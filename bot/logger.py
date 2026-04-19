import logging


def setup_logging(level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("orderbook_bot")
    if logger.handlers:
        logger.setLevel(level)
        return logger

    logger.setLevel(level)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03d | %(levelname)-7s | %(name)s | %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    return logger
