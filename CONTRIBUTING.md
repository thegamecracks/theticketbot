# Development Setup

When installing the project for development, you can enable [editable mode]
and install the [Jishaku] extension to help with iterative development and
debugging:

```sh
pip install --editable .[jishaku]
```

[editable mode]: https://setuptools.pypa.io/en/latest/userguide/development_mode.html
[Jishaku]: https://github.com/Gorialis/jishaku

You can also install this project's [pre-commit] hooks to automatically
run lints for you:

```sh
pip install pre-commit
pre-commit install
```

[pre-commit]: https://pre-commit.com/

And finally, you should use [Pyright] to type-check your code before committing.
In VSCode, this is built into the Pylance extension and can be enabled in
your settings, but you can also install the third-party pyright wrapper
to manually run it:

```sh
pip install pyright
pyright
```

[Pyright]: https://microsoft.github.io/pyright/

Database migration scripts are stored in [migrations/] and are automatically
executed upon bot startup. During development, if any changes to the database
schema are required, please create a backup of your database before adding a
new migration script.

[migrations/]: https://github.com/thegamecracks/theticketbot/tree/main/src/theticketbot/migrations/

When updating any file that contains `_()` translatable strings,
it is recommended to run `utils/merge_po.py` and `utils/build_mo.py`
just before starting the bot or creating a commit.
This requires gettext to be installed.

# Python Style Guide

- Code should follow [PEP 8] where possible, unless exempted by this guide
  - When unsure, run [Black] to format your code
  - Use `# fmt: off` and `# fmt: on` comments to override the formatter when necessary

- Unlike PEP 8, the max line length allowed in this codebase is 88 characters

- Variable names must **NOT** be abbreviated unless their usage is already
  conventional, such as `i`/`j` for indices or `c` for characters.
  In general, prefer explicit and readable names over short variable names.

  ```py
  # Bad:
  n = "thegamecracks"
  un = "thegamecracks"
  uName = "thegamecracks"
  # Good:
  user_name = "thegamecracks"
  ```

- Trailing commas **MUST** be used when arguments/elements are spread out
  over several lines
  - This includes single-length arguments/elements like `function(arg)`.
    If doing so would exceed the line length, consider refactoring the argument
    into a separate variable if not already done.

- Line continuations (`\`) are **NOT** allowed and should be managed with either
  implicit line continuations, decomposition of expressions into multiple statements,
  or refactoring into functions.

- All code must **NOT** have any trailing whitespace

- As an extension to PEP 8, imports should be grouped into the following order:
  - Built-in modules
  - Third-party modules
  - Absolute imports of local modules
  - Relative imports of local modules

  ```py
  import sqlite3
  import time
  from typing import Awaitable, Callable, Iterable

  import asqlite
  import discord
  from discord.ext import commands

  from theticketbot.database import DatabaseClient

  from .config import load_config
  ```

- Relatve imports **MAY** be used for sibling modules, i.e. those that reside
  in the same directory

- Absolute imports **MUST** be used for parent modules, i.e. those that exist
  outside of the module. In other words, relative imports consisting of two
  or more leadiing periods must be refactored into absolute imports.

  ```py
  # Bad:
  from ..database import DatabaseClient
  # Good:
  from theticketbot.database import DatabaseClient
  ```

[PEP 8]: https://peps.python.org/pep-0008/
[Black]: https://black.readthedocs.io/en/stable/
