"""Unified logging configuration for the forma application.

A single dictConfig that:
- Configures the root logger with a consistent format
- Makes uvicorn's loggers propagate to root (unified output, no duplicate handlers)
- Quiets noisy HTTP client libraries
"""

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s %(levelname)-8s %(name)s: %(message)s",
            "datefmt": "%H:%M:%S",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "default",
        }
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        # Uvicorn loggers: propagate to root so they share our format and handler
        "uvicorn": {"propagate": True, "level": "INFO"},
        "uvicorn.error": {"propagate": True, "level": "INFO"},
        "uvicorn.access": {"propagate": True, "level": "INFO"},
        # Quiet noisy HTTP client libraries
        "httpx": {"level": "WARNING"},
        "httpcore": {"level": "WARNING"},
    },
}
