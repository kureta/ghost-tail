from __future__ import annotations

import os

import loguru
from cysystemd.journal import JournaldLogHandler
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


def _journald_formatter(record: loguru.Record) -> str:
    """Log message formatter for journald."""
    return f"{record['level'].name}: {{module}}:{{function}}:{{line}}: {record['message']}"


def get_console() -> Console:
    """Get rich console."""
    if not hasattr(get_console, "console"):
        get_console.console = Console(color_system="truecolor", stderr=True)
    return get_console.console


def get_logger() -> loguru.Logger:
    if not hasattr(get_logger, "logger"):
        load_dotenv()
        log_level = os.getenv("LOG_LEVEL", "INFO")

        logger.remove()
        logger.add(
            get_console().print,
            enqueue=True,
            level=log_level,
            format=_log_formatter,
            colorize=True,
            backtrace=True,
            diagnose=True,
        )

        # Systemd journal logging does not support TRACE level
        # Default to INFO
        logger.add(
            JournaldLogHandler(identifier="Ghost Tail"),
            level="INFO",
            format=_journald_formatter,
        )

        get_logger.logger = logger

    return get_logger.logger
