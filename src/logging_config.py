from loguru import logger

_CONFIGURED = False


def setup_logger(log_path: str = "ai_agent.log"):
    global _CONFIGURED
    if _CONFIGURED:
        return logger

    # Remove default handler and configure
    logger.remove()
    logger.add(
        log_path,
        rotation="10 MB",
        retention="7 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
    )
    logger.add(
        lambda msg: print(msg),
        level="INFO",
        format="🤖 {time:HH:mm:ss} | {level} | {message}",
    )
    _CONFIGURED = True
    return logger

