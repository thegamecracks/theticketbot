import argparse
import asyncio
import functools
import getpass
import importlib.metadata
import logging
import os
import sys
from pathlib import Path
from typing import Type

from pydantic import SecretStr

from . import __version__
from .appdirs import APP_DIRS
from .bot import Bot, StartupFlags
from .config import load_config
from .logging import configure_logging

log = logging.getLogger(__package__)

USER_CONFIG = APP_DIRS.user_config_path / "config.toml"


def suppress(*exceptions: Type[BaseException]):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except exceptions:
                return

        return wrapper

    return decorator


@suppress(KeyboardInterrupt)
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
        help="The config file to load",
        type=Path,
    )
    commands = parser.add_mutually_exclusive_group()
    commands.add_argument(
        "--sync",
        action="store_const",
        const=StartupFlags.SYNC | StartupFlags.CLOSE,
        default=StartupFlags(0),
        dest="startup_flags",
        help="Sync application commands at startup",
    )
    commands.add_argument(
        "--dump-config",
        action="store_true",
        help="Dump config file at startup",
    )

    args = parser.parse_args()
    config_file: Path | None = args.config_file
    startup_flags: StartupFlags = args.startup_flags

    # Configure logging early to capture our own initialization
    configure_logging(args.verbose)

    if args.dump_config:
        dump_config_and_exit(config_file)

    if config_file is None:
        config_file = find_config_file()

    temp_config_file: Path | None = None
    if config_file is None:
        config_file = temp_config_file = prompt_and_create_config_file()
        startup_flags = StartupFlags.SYNC

    bot = Bot(
        functools.partial(load_config, config_file),
        startup_flags=startup_flags,
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
    asyncio.run(start(bot, temp_config_file))


def dump_config_and_exit(config_file: Path | None) -> None:
    if config_file is None:
        config_file = find_config_file()
    if config_file is None:
        sys.exit(
            "The config.toml file is not not present.\n"
            "Please run the bot normally to generate a configuration file,\n"
            "or write your own configuration file."
        )

    config = load_config(config_file)
    print(config_file)
    print(config.model_dump_json(indent=4, exclude={"bot": {"token"}}))
    sys.exit(1)


def find_config_file() -> Path | None:
    cwd_config = Path("config.toml")
    if USER_CONFIG.exists():
        if cwd_config.exists():
            log.warning(
                "\n"
                "Both the user-specific config.toml and CWD config.toml are present.\n"
                "Only the user config will be loaded.\n"
                "If you want to load the config.toml from CWD instead,\n"
                "add `--config-file config.toml` to your command-line arguments."
            )
        return USER_CONFIG
    elif cwd_config.exists():
        return cwd_config


def prompt_and_create_config_file() -> Path:
    print(
        f"No config.toml file was found in the current working directory.\n"
        f"A minimal config file will be written to:\n"
        f"\n"
        f"    {USER_CONFIG}\n"
        f"\n"
        f"Afterwards, the bot will automatically synchronize its application commands\n"
        f"and start itself. If an error occurs during this process, the config.toml\n"
        f"will be deleted so you can redo this.\n"
    )

    token = input_token()

    USER_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    with USER_CONFIG.open("w") as f:
        f.write("[bot]\n")
        f.write(f'token = "{token}"\n')

    return USER_CONFIG


def input_token() -> str:
    import getpass
    import re

    while True:
        token = getpass.getpass("Bot Token: ").strip()
        if re.fullmatch(r"\w+\.\w+\.\S+", token) is not None:
            return token

        print(
            "This token does not appear to be valid. It should look something like:\n"
            "    MTI0NjgyNjg0MTIzMTMyNzI3NQ.GTIAZm.x2fbSNuYJgpAocvMM53ROlMC23NixWt-0NOjMc\n"
            "Please try again."
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


async def start(bot: Bot, temp_config_file: Path | None) -> None:
    try:
        async with bot:
            await bot.login(bot.config.bot.token)

            # Token is valid, we no longer need to delete the temporary
            # config file if an error occurs now.
            temp_config_file = None

            await bot.connect(reconnect=True)
    except BaseException:
        if temp_config_file is not None:
            temp_config_file.unlink()
        raise


if __name__ == "__main__":
    main()
