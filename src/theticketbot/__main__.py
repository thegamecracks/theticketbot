import argparse
import functools
import getpass
import importlib.metadata
import logging
import os
import sys
from pathlib import Path

from pydantic import SecretStr

from . import __version__
from .bot import Bot
from .config import load_config
from .logging import configure_logging

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
    commands = parser.add_mutually_exclusive_group()
    commands.add_argument(
        "--sync",
        action="store_true",
        dest="sync_at_startup",
        help="Sync application commands at startup",
    )
    commands.add_argument(
        "--dump-config",
        action="store_true",
        help="Dump config file at startup",
    )

    args = parser.parse_args()
    config_file: Path = args.config_file
    sync_at_startup: bool = args.sync_at_startup

    # Configure logging early to capture our own initialization
    configure_logging(args.verbose)

    if args.dump_config:
        config = load_config(config_file)
        sys.exit(config.model_dump_json(indent=4, exclude={"bot": {"token"}}))

    bot = Bot(
        functools.partial(load_config, config_file),
        sync_at_startup=sync_at_startup,
    )

    check_outdated_database_path(bot.config.db.path, args.config_file)

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


def check_outdated_database_path(path: Path, config_file: str) -> None:
    if os.getenv("IGNORE_OUTDATED_DATABASE_PATHS") == "1":
        return

    outdated_paths = [Path("data/theticketbot.db")]
    for outdated in outdated_paths:
        if path.resolve() == outdated.resolve():
            return
        elif not outdated.exists():
            continue
        elif outdated.is_symlink():
            continue

        log.warning(
            f"\n"
            f"A database file was found at {outdated} but db.path is set to\n"
            f"{path}.\n"
            f"\n"
            f"It is recommended you move your database file to db.path\n"
            f"so theticketbot can continue using the database.\n"
            f"\n"
            f"If you want to keep using your database file at {outdated},\n"
            f'please set path = "{outdated}" in the [db] table\n'
            f"of your config file, {config_file}.\n"
            f"\n"
            f"If you are absolutely sure your database files are correctly placed,\n"
            f"you may suppress this warning by setting the environment variable\n"
            f"IGNORE_OUTDATED_DATABASE_PATHS=1."
        )
        return


if __name__ == "__main__":
    main()
