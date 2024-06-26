import datetime
import json
import logging
import logging.handlers
from typing import Any

import discord

from .appdirs import APP_DIRS

LOG_RECORD_ATTRIBUTES = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",  # cached by formatException()
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "message",
    "module",
    "msecs",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}

log = logging.getLogger(__package__)


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = self._prepare_record(record)
        return json.dumps(data, default=str)

    def _prepare_record(self, record: logging.LogRecord) -> dict[str, Any]:
        data = {}

        for k, v in vars(record).items():
            if k not in LOG_RECORD_ATTRIBUTES:
                data[k] = v

        created = datetime.datetime.fromtimestamp(
            record.created,
            tz=datetime.timezone.utc,
        )

        data["created"] = created.isoformat()
        data["level"] = record.levelname
        data["name"] = record.name
        data["message"] = record.getMessage()

        if record.exc_info is not None:
            data["exc_info"] = self.formatException(record.exc_info)

        if record.stack_info is not None:
            data["stack_info"] = self.formatStack(record.stack_info)

        return data


def configure_logging(verbose: int) -> None:
    root_level = logging.INFO
    if verbose > 0:
        log.setLevel(logging.DEBUG)
    if verbose > 1:
        root_level = logging.DEBUG

    discord.utils.setup_logging(level=root_level, root=True)

    APP_DIRS.user_log_path.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        str(APP_DIRS.user_log_path / f"{__package__}.jsonl"),
        maxBytes=5_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(JSONFormatter())
    logging.getLogger().addHandler(handler)
