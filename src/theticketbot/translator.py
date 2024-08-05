from __future__ import annotations

import importlib.resources
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator

import discord
from discord import app_commands
from discord.app_commands import TranslationContextLocation, locale_str as _locale_str
from discord.ext import commands
from fluent_compiler.bundle import FluentBundle
from fluent_compiler.errors import FluentReferenceError

if TYPE_CHECKING:
    from .bot import Bot

assert __package__ is not None
_LOCALES_PATH = Path(str(importlib.resources.files(__package__).joinpath("locales")))


def yield_ftl_paths() -> Iterator[tuple[str, list[Path]]]:
    if not _LOCALES_PATH.is_dir():
        return

    for locale in _LOCALES_PATH.iterdir():
        yield locale.name, list(locale.glob("*.ftl"))


class FluentBackend:
    def __init__(self) -> None:
        ftl_paths = list(yield_ftl_paths())
        ftl_paths = [(locale.replace("_", "-"), paths) for locale, paths in ftl_paths]
        self.bundles = {
            discord.Locale(locale): FluentBundle.from_files(
                locale, list(map(str, paths))
            )
            for locale, paths in ftl_paths
        }

        for locale, bundle in self.bundles.items():
            errors = bundle.check_messages()
            if len(errors) > 0:
                raise ValueError(f"Failed to parse {locale} localizations: {errors}")

        self.bundles[discord.Locale("en-GB")] = self.bundles[discord.Locale("en-US")]

    def translate(
        self,
        string: _locale_str,
        locale: discord.Locale = discord.Locale("en-US"),
        data: Any = None,
        *,
        ignore_missing_data: bool = False,
    ) -> str | None:
        bundle = self.bundles.get(locale)
        if bundle is None:
            return

        message_id = string.extras.get("id", string.message)
        translated, errors = bundle.format(message_id, data)

        if ignore_missing_data:
            errors = [e for e in errors if not isinstance(e, FluentReferenceError)]

        if len(errors) > 0:
            raise ValueError(f"Failed to translate {string!r}: {errors}")

        return translated or None


fluent = FluentBackend()


class FluentTranslator(app_commands.Translator):
    async def translate(
        self,
        string: _locale_str,
        locale: discord.Locale,
        context: app_commands.TranslationContextTypes,
    ) -> str | None:
        if context.location == TranslationContextLocation.choice_name:
            data = context.data.value
        else:
            data = context.data

        return fluent.translate(string, locale, data)


def locale_str(string: str, **kwargs: Any) -> _locale_str:
    """Creates a locale_str where the message is replaced with the en-US
    translation.

    This ensures unsupported languages will at least see the English localization
    instead of the message ID itself.

    If an id= is defined, the string will be passed through without replacement.

    """
    if "id" not in kwargs:
        translated = fluent.translate(
            _locale_str(string, **kwargs),
            ignore_missing_data=True,
        )
        if translated is None:
            raise ValueError(f"Missing en-US localization for {string}")

        kwargs["id"] = string
        string = translated

    return _locale_str(string, **kwargs)


async def translate(
    message: _locale_str,
    obj: Bot | discord.Interaction,
    *,
    locale: discord.Locale | None = None,
    data: Any = None,
) -> str:
    """A shorthand for translating a message.

    Unlike the methods built into discord.py, this will use the original message
    if a translation could not be found.

    """
    if isinstance(obj, commands.Bot):
        if locale is None:
            locale = discord.Locale("en-US")

        assert obj.tree.translator is not None
        context = app_commands.TranslationContext(
            location=app_commands.TranslationContextLocation.other,
            data=data,
        )
        translated = await obj.tree.translator.translate(
            message,
            locale=locale,
            context=context,
        )
    else:
        translated = await obj.translate(
            message,
            data=data,
            locale=locale or obj.locale,
        )

    return translated or str(message)
