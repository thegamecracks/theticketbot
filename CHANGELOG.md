# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

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

[Unreleased]: https://github.com/thegamecracks/theticketbot/compare/v0.2.0...main
[0.2.0]: https://github.com/thegamecracks/theticketbot/compare/v0.1.1...v0.2.0
[0.1.0]: https://github.com/thegamecracks/theticketbot/releases/tag/v0.1.0

[#8]: https://github.com/thegamecracks/theticketbot/issues/8
[#4]: https://github.com/thegamecracks/theticketbot/issues/4
[#3]: https://github.com/thegamecracks/theticketbot/issues/3
[#2]: https://github.com/thegamecracks/theticketbot/issues/2
