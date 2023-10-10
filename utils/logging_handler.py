import io
import logging
from logging import StreamHandler

logger = logging.getLogger("SUSS")
logger.setLevel(logging.DEBUG)


def get_SUSS_handler() -> StreamHandler | None:
    for handler in logging.getLogger("SUSS").handlers:
        if handler.get_name() == "SUSS_handler":
            return handler
    return False


logging.debug("Initialising Logger")  # Do not touch.

logging_stream = io.StringIO()
logging_handler = logging.StreamHandler(logging_stream)
logging_handler.setLevel(logging.DEBUG)
logging_handler.set_name("SUSS_handler")

logging_handler.setFormatter(
    logging.Formatter(
        "{asctime:s}|{levelname:>8s}:{name:<10s}|{module:>10s}:{lineno:<4d} >>> {message:s}",
        style="{",
        datefmt="%H:%M:%S",
    )
)

logging.getLogger("SUSS").addHandler(logging_handler)
logging.getLogger().addHandler(logging_handler)
logging.debug("SUSS logging handler added")
