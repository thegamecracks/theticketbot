# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.4.2] - 2024-06-26

### New Features

- Automatically prompt to create a config.toml file in a user config directory
  if no config file is found ([#10])
  - If a config.toml is found in the current working directory and the
    new user config isn't present, it will be loaded to preserve backwards
    compatibility.
  - This behaviour can be bypassed using the `--config-file` argument.
- Print loaded config file's path when using `--dump-config`

### Changes

- Suppress KeyboardInterrupt tracebacks in the CLI more reliably

### Fixes

- Fix untranslated message when clicking "Create Ticket" on an unrecognized inbox
- Raise an exception when `--config-file` is given a non-existent file path

## [0.4.1] - 2024-06-26

### New Features

- Add .jsonl logging to user log directory

### Changes

- Replace hardcoded owner mention shown in error messages
  with the real bot owner given by the Discord API
- Clarify gettext dependency in readme

### Fixes

- Don't unnecessarily create application / temporary directories at startup

## [0.4.0.post1] - 2024-06-26

This release adds a couple badges to the readme and fixes the readme image
not showing up on the PyPI page.

## [0.4.0] - 2024-06-26

This is theticketbot's first release to go on [PyPI](https://pypi.org/project/theticketbot/)! 🎉

### Changes

- BREAKING CHANGE:
  The default database path now defaults to a user-specific directory
  on your current platform.
  - This path can be revealed by running `theticketbot --dump-config`.
  - Users who want to revert to the old behaviour must explicitly write
    `path = "data/theticketbot.db"` in their config file's `[db]` table.
- Add classifiers, license, keywords, and URLs to the project's metadata
- Unpin discord.py to `~=2.4`
- Use PyPI version of asqlite pinned at `==2.0.0`

### Fixes

- Disable the polls intent by default, and don't enable any future standard intents
  when upgrading discord.py

## [0.3.2] - 2024-06-19

### New Features

- Add french localization, courtesy of @Bubobubobubobubo
- Add `--sync` command-line argument to make registering application commands easier

## [0.3.1] - 2024-06-17

### New Features

- Automatically lock tickets when archived by staff / auto-archived,
  and bot is given Manage Threads permission ([#5])

## [0.3.0] - 2024-06-10

### New Features

- Add german localization, courtesy of @GamingGalaxy200
- Add `/inbox message` for editing inbox messages in-place ([#2])
- Add `/inbox staff` all-in-one command for adding, listing, and removing inbox staff
- Use per-channel Manage Threads permission to automatically add staff for new inboxes ([#8])
- Prompt to select messages after using a command instead of requiring a selection beforehand ([#3])
  - This should make the user experience easier overall, but may make it less convenient to perform multiple commands on the same message.
- Automatically cleanup deleted roles from inbox staff ([#4])
- Automatically archive tickets when their owner leaves the server
- Optionally lock tickets during archival when the bot is given the Manage Threads permission
- Add `theticketbot` console script as an alternative to `python -m theticketbot`
  - Supports running with [pipx](https://pipx.pypa.io/latest/), if desired
- Add experimental support for encrypted SQLite databases
  - See the [README](https://github.com/thegamecracks/theticketbot/blob/v0.3.0/README.md#encryption) for usage

### Changes

- Make `/inbox` command guild-only
- Don't include commas in the `$staff` placeholder for ticket starters
- Rename `$name` to `$author` in ticket name placeholders
  - This is automatically applied to existing inboxes during database migrations.
- Don't request guild members during startup
  - This can significantly reduce unnecessary bandwidth when added to large guilds.
- For user convenience, reset timeouts for message selection commands when an error occurs
  - Previously, the selection would always timeout 180s after the initial slash command even if the user was selecting messages.
- Remove Manage Server permission check on inbox message selections
  - This is no longer needed since the new message selection system is isolated to each guild, preventing users from attempting to manage inboxes from other guilds. Admins can now grant the `/inbox` command to staff that don't have the Manage Server permission.

### Fixes

- Fix deleted threads not being removed from database while bot is online

### Removals

- `/inbox staff add`
- `/inbox staff list`
- `/inbox staff remove`

## [0.2.0] - 2024-06-04

### New Features

- Add `/inbox new-tickets name` for customizing names of new tickets
  - See the [README](https://github.com/thegamecracks/theticketbot/blob/v0.2.0/README.md#customization) for available placeholders
- Allow customizing per-user inbox ratelimits with native channel slowmode settings
  - As of now, this ratelimit cannot be lower than 60 seconds.
- Automatically archive tickets after being left by their owners
- Show a helpful message when creating a ticket on an unrecognized inbox
- Automated clean up of obsolete guilds in database, running every saturday

### Changes

- Update intents in default configuration:
  - `members = true`
    - This is needed to track when ticket owners leave their thread.
  - `message_content = false`
    - For now, all message content needed for bot functionality can be received without this intent.
- Use [setuptools-scm](https://setuptools-scm.readthedocs.io/en/latest/) in build system
  - Version automatically changes according to Git repository tags
  - All tracked files are now included in source distributions

### Removals

- `/inbox starter get`
- `/inbox starter set` - renamed to `/inbox new-tickets starter`

## [0.1.0] - 2024-06-03

This is theticketbot's first release! 🎉

[Unreleased]: https://github.com/thegamecracks/theticketbot/compare/v0.4.2...main
[0.4.2]: https://github.com/thegamecracks/theticketbot/compare/v0.4.1...v0.4.2
[0.4.1]: https://github.com/thegamecracks/theticketbot/compare/v0.4.0.post1...v0.4.1
[0.4.0.post1]: https://github.com/thegamecracks/theticketbot/compare/v0.4.0...v0.4.0.post1
[0.4.0]: https://github.com/thegamecracks/theticketbot/compare/v0.3.2...v0.4.0
[0.3.2]: https://github.com/thegamecracks/theticketbot/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/thegamecracks/theticketbot/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/thegamecracks/theticketbot/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/thegamecracks/theticketbot/compare/v0.1.1...v0.2.0
[0.1.0]: https://github.com/thegamecracks/theticketbot/releases/tag/v0.1.0

[#10]: https://github.com/thegamecracks/theticketbot/issues/10
[#8]: https://github.com/thegamecracks/theticketbot/issues/8
[#5]: https://github.com/thegamecracks/theticketbot/issues/5
[#4]: https://github.com/thegamecracks/theticketbot/issues/4
[#3]: https://github.com/thegamecracks/theticketbot/issues/3
[#2]: https://github.com/thegamecracks/theticketbot/issues/2
