# theticketbot

[![](https://img.shields.io/pypi/v/theticketbot?style=flat-square)](https://pypi.org/project/theticketbot/)
[![](https://img.shields.io/github/actions/workflow/status/thegamecracks/theticketbot/pyright-lint.yml?style=flat-square&label=pyright)](https://microsoft.github.io/pyright/#/)

A simple Discord bot for handling ticket systems using channel threads.

![](https://raw.githubusercontent.com/thegamecracks/theticketbot/main/docs/images/demo.png)

## Resources

- Issues: https://github.com/thegamecracks/theticketbot/issues?q=
- Milestones: https://github.com/thegamecracks/theticketbot/milestones
- Releases: https://github.com/thegamecracks/theticketbot/releases

## Contributing

Before submitting any changes, please read and follow the [Contributing Guide]!

[Contributing Guide]: https://github.com/thegamecracks/theticketbot/blob/main/CONTRIBUTING.md

Want to help out by adding translations? This bot stores them in the [locales/]
directory. You can [fork this repository], create a new branch, commit your
PO files there, and make a pull request!
See [discord.py-gettext-demo's onboarding] for more information.

[locales/]: https://github.com/thegamecracks/theticketbot/tree/main/src/theticketbot/locales/
[fork this repository]: https://docs.github.com/en/get-started/quickstart/contributing-to-projects
[discord.py-gettext-demo's onboarding]: https://github.com/thegamecracks/discord.py-i18n-demo/blob/main/docs/en/onboarding.md

## Usage

I am not hosting a public instance of this bot, and I have no endorsements
for any bots that claim to host this project. Sorry for the inconvenience!
If you're technically inclined, you can host this bot yourself.

With Python 3.11+, you can set up this bot by following these steps:

1. Create a virtual environment and install theticketbot from PyPI:

   ```sh
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   pip install theticketbot
   ```

   Alternatively, you can install the latest, in-development version using Git:

   ```sh
   pip install git+https://github.com/thegamecracks/theticketbot
   ```

   When installing from the source code like above, localizations may be
   compiled using gettext's `msgfmt` program if it is available on your system.
   This dependency is not needed when installing the wheel distributions
   from PyPI as they already contain the localizations pre-compiled.
   If you don't have gettext when installing from source, localizations
   will be disabled.

2. Start the bot:

   ```sh
   theticketbot
   # or
   python -m theticketbot
   ```

   You will be prompted to enter your bot token so it can be written to
   a [config.toml] file in a user-specific directory. After this, the bot
   will automatically synchronize its application commands for the first time.

   If you update the bot later on, you may need to run `theticketbot --sync`
   to synchronize the bot's application commands again.
   See the [changelog] to know if this is needed.

   Alternatively, you can use the "<@mention> sync" text command once your bot
   is in a server to synchronize application commands.

3. Create an invite link in the Discord Developer Portal to add your bot to a server.

   In the [Applications](https://discord.com/developers/applications) > OAuth2 page,
   select only `bot` for the scope, then in the permissions list below,
   select at least the following permissions:

   - Read Messages/View Channels
   - Send Messages
   - Create Private Threads
   - Send Messages in Threads
   - Embed Links
   - Attach Files

   A few other permissions like Manage Threads and Mention Everyone
   may be useful, but are not required.

   Leave the Integration Type as "Guild Install", and copy the generated URL
   at the bottom. You can now use that URL to invite the bot or let others
   invite the bot if "Public Bot" is ticked in the Bot page.

[config.toml]: https://github.com/thegamecracks/theticketbot/blob/main/src/theticketbot/config_default.toml
[changelog]: https://github.com/thegamecracks/theticketbot/blob/main/CHANGELOG.md

To set up an inbox, first post a message with the content you would like your
inbox message to have. This message may include image attachments, or custom
embeds sent by a webhook as long as the message has no content.

Afterwards, use `/inbox create` to choose the channel you want your inbox posted in.
You will then be prompted to select a message to be sent with your inbox.
You can then right-click or long tap the message you sent, open the Apps menu,
and use `Select this message`.

When choosing a channel, the bot must be able to view, send messages,
and create private threads in that channel.

Each inbox has a set of staff that will be mentioned when a new ticket is created.
Any members or roles that you explicitly grant Manage Threads in the channel's
permissions will be automatically added as staff for the inbox, but you can
change this later with `/inbox staff`.

Tickets are managed using Discord's native thread functionality.
Closing the thread archives it, preserving their messages without
needing a separate transcript.
Staff with the Manage Threads permission can also add and remove members,
useful for bringing in relevant members or for removing the ticket owner
to allow internal discussions inside the ticket. Tickets can be renamed
to make them more easily searchable, and can be deleted permanently if desired.

If the owner leaves or is removed from their ticket, the bot will automatically
archive the ticket. Staff are free to re-open it afterwards.

The bot will also lock the ticket to prevent further discussion if it has
the Manage Threads permission, which can be set on a per-channel basis.
In this case, staff must have the Manage Threads permission to re-open the
ticket.

If you have multiple inboxes in one channel, any staff with the Manage Threads
permission will be able to view and manage all threads in that channel
even if they aren't listed as staff for those inboxes.
If maintaining privacy is important, inboxes should be organized into
different channels according to which staff should be allowed to view
the threads of those inboxes. This layout can look like:

- `#mod-tickets` (moderators have Manage Threads)
  - `General Support`
  - `Member Reports`
- `#admin-tickets` (admins have Manage Threads)
  - `Ban Appeals`
  - `Feedback And Suggestions`
  - `Staff Applications`

Alternatively, you can choose to not grant the Manage Threads permission to staff.
This will prevent them from closing tickets, inviting other members,
or sending messages in locked tickets.
This also means future staff members won't be able to view older tickets.

## Customization

There are various settings that can be customized for each inbox.
When you use the below commands, you will be prompted to select the message
of the inbox that you want to change, i.e. the message that has the
Create Ticket button.

- `/inbox message`

  Edit the message of an inbox with a new message.

- `/inbox staff`

  Inspect and manage staff members/roles for an inbox.

- `/inbox new-tickets starter`

  Inspect the starting message for new tickets and optionally change it.

  Allowed placeholders are:

  - `$author`

    The ticket owner's mention. Must be included in the message
    for the owner to be invited.

  - `$staff`

    A list of mentions for the inbox's staff members and roles.
    Must be included in the message for staff to be invited
    if they do not have the Manage Threads permission.

  For example, a starting message for a moderation inbox might look like:

  ```
  $author Thank you for creating a moderation ticket! $staff will be with you shortly.
  ```

  Note that role mentions require either the role to be mentionable or the bot
  to have the *Mention all roles* permission in the inbox's channel.

- `/inbox new-tickets name`

  Inspect and manage the default name for new tickets.

  Allowed placeholders are:

  - `$year`
  - `$month`
  - `$day`
  - `$author`

    The ticket owner's display name.

  - `$counter`

    An incrementing 4-digit counter starting from 0001.

    Upon exceeding 9999, the counter will overflow back to 0000.
    The counter is not guaranteed to be sequential and may skip
    if the bot is unsuccessful in creating a ticket.

  Thread names will be limited to 100 characters by Discord.

## Ticket Limits

Each inbox limits users to a minimum of 1 thread every 60 seconds.
If a channel slowmode above 60 seconds is set, the inbox will match
that delay to limit new tickets.

Inboxes will also try to limit users to 1 active thread per inbox,
but may not be guaranteed due to technical limitations.

## Encryption

> [!WARNING]
>
> This feature is experimental and may be removed in the future.
>
> This bot does not store any sensitive data on users and persists only
> the bare minimum needed to function, so encrypting the database is not
> significantly useful in contrast to protecting your bot's token.
>
> Encryption is also not a substitute for properly configured file permissions.
> You should ensure that other users on your system are not able to read the
> database or the config.toml file. Other secure methods of transferring
> these files between systems should be applied as well.
>
> Finally, derived keys are not cached by the bot, meaning that every connection
> made to the database, which can be several connections per command, requires
> repeating the same key derivation which may be performance intensive.

This bot supports using an encrypted SQLite database with encryption extensions
like [SQLiteMultipleCiphers], [SQLCipher], or [SEE]. On a Windows system,
pre-built DLLs can be found for SQLiteMultipleCiphers in their
[releases](https://github.com/utelle/SQLite3MultipleCiphers/releases) page.

With one of the encryption extensions installed, you can use it to encrypt
the database and then add the decryption to theticketbot. Run the bot once
so your database file is created - use `theticketbot --dump-config` to locate it
if you didn't explicitly set a `db.path` in your config - then open the database
using the SQLite shell from your encryption extension and encrypt it:

```sql
$ sqlite3 theticketbot.db
SQLite version 3.46.0 2024-05-23 13:25:27 (UTF-16 console I/O) (SQLite3 Multiple Ciphers 1.8.5)
Enter ".help" for usage hints.
sqlite> PRAGMA rekey = 'Hello world!';
sqlite> .exit
```

After that, open your config.toml file and add a template for the pragma
to decrypt your database like so:

```toml
[db]
key_template = "PRAGMA key = '{}'"
```

A more complex encryption setup might look like:

```toml
[db]
pragmas = ["PRAGMA cipher = sqlcipher", "PRAGMA kdf_iter = 512000"]
key_template = "PRAGMA hexkey = '{}'"
```

At startup, you will be prompted to enter the database key.
Once the database is opened, all pragmas will be executed in order.
To change the encryption key later, shut down the bot and then manually execute
the necessary pragmas according to the documentation for your encryption extension.

If you get an error like `file is not a database` or `unsupported file format`,
this may mean that the bot was unable to decrypt the database, or that the database
hasn't yet been encrypted. In this case, please double check your pragmas and/or
try to manually decrypt your database in an SQLite shell.

During encryption, if you get `Rekeying is not supported in WAL journal mode`,
you will need to run `PRAGMA journal_mode = delete;` before rekeying.

[SQLiteMultipleCiphers]: https://utelle.github.io/SQLite3MultipleCiphers/
[SQLCipher]: https://www.zetetic.net/sqlcipher/documentation/
[SEE]: https://sqlite.org/com/see.html

## License

This project is written under the [MIT] license.

[MIT]: https://github.com/thegamecracks/theticketbot/blob/main/LICENSE
