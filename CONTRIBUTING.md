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
