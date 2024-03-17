from __future__ import annotations

import os

import loguru
from dotenv import load_dotenv
from loguru import logger
from rich.console import Console


def _get_record_color(record: loguru.Record) -> str:
    """Get color for log message."""
    color_map = {
        "TRACE": "dim blue",
        "DEBUG": "cyan",
        "INFO": "bold",
        "SUCCESS": "bold green",
        "WARNING": "yellow",
        "ERROR": "bold red",
        "CRITICAL": "bold white on red",
    }
    return color_map.get(record["level"].name, "cyan")


def _log_formatter(record: loguru.Record) -> str:
    """Log message formatter."""
    color = _get_record_color(record)
    return (
        f"[not bold green]{record['time']:YYYY/MM/DD HH:mm:ss}[/not bold green] | "
        f"{record['level'].icon} | {{module}}:{{function}}:{{line}}\t- [{color}]{{message}}[/{color}]"
    )


class SingletonConsole(Console):
    """Singleton console class"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SingletonConsole, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        super().__init__(color_system="truecolor", stderr=True)


def get_logger() -> loguru.Logger:
    if not hasattr(get_logger, "logger"):
        load_dotenv()
        log_level = os.getenv(key="LOG_LEVEL", default="INFO")

        logger.remove()
        logger.add(
            SingletonConsole().print,
            enqueue=True,
            level=log_level,
            format=_log_formatter,
            colorize=True,
            backtrace=True,
            diagnose=True,
        )

        get_logger.logger = logger

    return get_logger.logger
