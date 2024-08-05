Hello and welcome to theticketbot's codebase!
Here is a summary of the file structure here:

- [`cogs/`](cogs/): Contains hot-reloadable functionality for this app.
- [`locales/`](locales/): Provides translations for user-facing messages.
- [`migrations/`](migrations/): Defines SQL migrations for the SQLite database.
- [`__init__.py`](__init__.py): Marks this directory as a package.
- [`__main__.py`](__main__.py): Provides the command-line interface.
- [`appdirs.py`](appdirs.py): Defines user-specific directory paths for the application.
- [`bot.py`](bot.py): Defines the bot class used for connecting to Discord.
- [`config.py`](config.py): Handles loading and validating the configuration file.
- [`config_default.toml`](config_default.toml): The default configuration file.
- [`database.py`](database.py): Provides methods for connecting to the database and executing common queries.
- [`errors.py`](errors.py): Defines exceptions used in this app.
- [`logging.py`](logging.py): Handles configuring the app's stream and file logging.
- [`migrations.py`](migrations.py): Handles versioning and execution of SQLite migrations.
- [`translator.py`](translator.py): Integrates translations with discord.py.
- [`versions.py`](versions.py): Defines comparison functions for [PEP 440] version strings.

[PEP 440]: https://packaging.python.org/en/latest/specifications/version-specifiers/
