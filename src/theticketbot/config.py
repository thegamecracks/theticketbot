from __future__ import annotations

import importlib.resources
import tomllib
from pathlib import Path
from typing import IO, TYPE_CHECKING, Annotated, Any, Literal, Protocol

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    SecretStr,
    ValidationInfo,
    ValidatorFunctionWrapHandler,
    WrapValidator,
)

from .appdirs import expand_app_dirs

if TYPE_CHECKING:
    import discord

assert __package__ is not None
_package_files = importlib.resources.files(__package__)
CONFIG_DEFAULT_RESOURCE = _package_files.joinpath("config_default.toml")


class _BaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# https://docs.pydantic.dev/usage/settings/
class Settings(_BaseModel):
    bot: SettingsBot
    db: SettingsDB


class SettingsBot(_BaseModel):
    allow_jishaku: bool
    extensions: list[str]
    inbox: SettingsBotInbox
    intents: SettingsBotIntents
    token: str


class SettingsBotInbox(_BaseModel):
    max_attachment_size: int
    """The max cumulative size allowed for an inbox message's attachments."""


class SettingsBotIntents(_BaseModel):
    """The intents used when connecting to the Discord gateway.

    .. seealso:: https://discordpy.readthedocs.io/en/stable/api.html#intents

    """

    model_config = ConfigDict(extra="allow")

    def create_intents(self) -> discord.Intents:
        import discord

        return discord.Intents(**self.model_dump())


def expand_app_dirs_strict(s: str) -> str:
    try:
        return expand_app_dirs(s, strict=True)
    except KeyError as e:
        raise ValueError(f"{e.args[0]} not a valid variable") from None


def check_pragma_statement(s: SecretStr) -> SecretStr:
    if not s.get_secret_value().strip().lower().startswith("pragma"):
        raise ValueError("statement must start with PRAGMA")
    return s


def check_single_statement(s: SecretStr) -> SecretStr:
    s_new = s.get_secret_value().rstrip(";")
    if ";" in s_new:
        raise ValueError("string must consist of a single statement")
    return SecretStr(s_new)


def pass_through_empty_string(
    s: str,
    handler: ValidatorFunctionWrapHandler,
    info: ValidationInfo,
) -> SecretStr:
    if s == "":
        return SecretStr(s)
    return handler(s)


class SettingsDB(_BaseModel):
    path: Annotated[Path, BeforeValidator(expand_app_dirs_strict)]
    """The filepath to write the bot's SQLite database to."""
    pragmas: list[
        Annotated[
            SecretStr,
            AfterValidator(check_single_statement),
            AfterValidator(check_pragma_statement),
        ]
    ]
    """A list of pragmas used to initialize the database."""
    key_template: Annotated[
        SecretStr,
        AfterValidator(check_single_statement),
        AfterValidator(check_pragma_statement),
        WrapValidator(pass_through_empty_string),
    ]
    """The pragma template used to prompt for the passphrase upon startup."""


Settings.model_rebuild()
SettingsBot.model_rebuild()


class OpenableBinary(Protocol):
    def open(self, __mode: Literal["rb"], /) -> IO[bytes]: ...


def _recursive_update(dest: dict, src: dict) -> None:
    for k, vsrc in src.items():
        vdest = dest.get(k)
        if isinstance(vdest, dict) and isinstance(vsrc, dict):
            _recursive_update(vdest, vsrc)
        else:
            dest[k] = vsrc


def _load_raw_config(path: OpenableBinary) -> dict[str, Any]:
    with path.open("rb") as f:
        return tomllib.load(f)


def load_default_config() -> Settings:
    """Loads the default configuration file.

    :returns: The settings that were parsed.
    :raises FileNotFoundError:
        The default configuration file could not be found.

    """
    data = _load_raw_config(CONFIG_DEFAULT_RESOURCE)
    return Settings.model_validate(data)


def load_config(path: Path, *, merge_default: bool = True) -> Settings:
    """Loads the bot configuration file.

    :param merge_default:
        If True, the default configuration file will be used as a base
        and the normal configuration is applied on top of it,
        if it exists.
    :returns: The settings that were parsed.
    :raises FileNotFoundError:
        Either the configuration file could not be found,
        or the default configuration file could not be found.

    """
    if not merge_default:
        data = _load_raw_config(path)
    else:
        data = _load_raw_config(CONFIG_DEFAULT_RESOURCE)
        overwrites = _load_raw_config(path)
        _recursive_update(data, overwrites)

    return Settings.model_validate(data)
