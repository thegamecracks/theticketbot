from __future__ import annotations

import importlib.resources
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator

import discord
from discord import app_commands
from discord.app_commands import TranslationContextLocation
from discord.ext import commands
from fluent_compiler.bundle import FluentBundle

if TYPE_CHECKING:
    from .bot import Bot

assert __package__ is not None
_LOCALES_PATH = Path(str(importlib.resources.files(__package__).joinpath("locales")))


def yield_ftl_paths() -> Iterator[tuple[str, list[Path]]]:
    if not _LOCALES_PATH.is_dir():
        return

    for locale in _LOCALES_PATH.iterdir():
        yield locale.name, list(locale.glob("*.ftl"))


class FluentTranslator(app_commands.Translator):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

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

    async def translate(
        self,
        string: app_commands.locale_str,
        locale: discord.Locale,
        context: app_commands.TranslationContextTypes,
    ) -> str | None:
        bundle = self.bundles.get(locale)
        if bundle is None:
            return

        if context.location == TranslationContextLocation.choice_name:
            data = context.data.value
        else:
            data = context.data

        message_id = string.extras.get("id", string.message)
        translated, errors = bundle.format(message_id, data)
        if len(errors) > 0:
            raise ValueError(f"Failed to translate {string!r}: {errors}")

        return translated or None


async def translate(
    message: app_commands.locale_str,
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
