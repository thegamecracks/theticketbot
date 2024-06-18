import argparse
import functools
import getpass
import importlib.metadata
import logging
import sys
from pathlib import Path

import discord
from pydantic import SecretStr

from . import __version__
from .bot import Bot
from .config import load_config

log = logging.getLogger(__package__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog=__package__,
        description=importlib.metadata.metadata("theticketbot")["Summary"],
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase logging verbosity",
    )
    parser.add_argument(
        "--config-file",
        default="config.toml",
        help="The config file to load",
        type=Path,
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        dest="sync_at_startup",
        help="Sync application commands at startup",
    )

    args = parser.parse_args()
    config_file: Path = args.config_file
    sync_at_startup: bool = args.sync_at_startup

    root_level = logging.INFO
    if args.verbose > 0:
        log.setLevel(logging.DEBUG)
    if args.verbose > 1:
        root_level = logging.DEBUG

    # Configure logging early to capture our own initialization
    discord.utils.setup_logging(
        level=root_level,
        root=True,
    )

    bot = Bot(
        functools.partial(load_config, config_file),
        sync_at_startup=sync_at_startup,
    )

    if bot.config.bot.token == "":
        sys.exit(
            "No bot token has been supplied by the config file.\n"
            "Please get a Bot Token from https://discord.com/developers/applications "
            "and add it to your configuration."
        )

    key_template = bot.config.db.key_template.get_secret_value()
    if key_template != "":
        key = getpass.getpass("Database Key: ")
        pragma = key_template.format(key)
        bot.key_pragma = SecretStr(pragma)

    log.info(f"Package version: {__version__}")
    bot.run(
        bot.config.bot.token,
        log_handler=None,
    )


if __name__ == "__main__":
    main()
