# theticketbot

A simple Discord bot for handling ticket systems using channel threads.

![](/docs/images/demo.png)

## Resources

- Issues: https://github.com/thegamecracks/theticketbot/issues?q=
- Milestones: https://github.com/thegamecracks/theticketbot/milestones
- Releases: https://github.com/thegamecracks/theticketbot/releases

## Contributing

Before submitting any changes, please read and follow the [Contributing Guide]!

[Contributing Guide]: /CONTRIBUTING.md

Want to help out by adding translations? This bot stores them in the [locales/]
directory. You can [fork this repository], create a new branch, commit your
PO files there, and make a pull request!
See [discord.py-gettext-demo's onboarding] for more information.

[locales/]: /src/theticketbot/locales/
[fork this repository]: https://docs.github.com/en/get-started/quickstart/contributing-to-projects
[discord.py-gettext-demo's onboarding]: https://github.com/thegamecracks/discord.py-i18n-demo/blob/main/docs/en/onboarding.md

## Usage

I am not hosting a public instance of this bot, and I have no endorsements
for any bots that claim to host this project. Sorry for the inconvenience!
If you're technically inclined, you can host this bot yourself.

`gettext` is an optional dependency. During installation, `msgfmt` will be
invoked if available to compile localizations.

With Python 3.11+ and Git, you can set up this bot by following these steps:

1. Clone this repository:

   ```sh
   git clone https://github.com/thegamecracks/theticketbot
   cd theticketbot
   ```

2. Create a virtual environment and install the project to it:

   ```sh
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   pip install -e .
   ```

3. Create a [config.toml] file containing your bot token:

   ```toml
   [bot]
   token = "Bot token from https://discord.com/developers/applications"
   ```

4. Start the bot:

   ```sh
   theticketbot
   # or
   python -m theticketbot
   ```

5. Invite your bot to a server and use "<@mention> sync" to synchronize
   the bot's application commands.

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

[config.toml]: /src/theticketbot/config_default.toml

To set up an inbox, first post a message with the content you would like your
inbox message to have. This message may include image attachments, or custom
embeds sent by a webhook as long as the message has no content.

Afterwards, use `/inbox create` to choose the channel you want your inbox posted in.
You will then be prompted to select a message to be sent with your inbox.
For a short period of time, you can right-click or long tap any message,
open the Apps menu, and use `Select this message`. The bot must be able
to view, send messages, and create private threads in that channel.
Currently, there are no limits on the number of inboxes your server can have.

Tickets are managed just like threads. Closing them archives the thread,
preserving their messages without needing a separate transcript. Staff with
the Manage Threads permission can also add and remove members afterwards,
useful for bringing in relevant members or for privating the thread to
continue internal discussions. Tickets can be renamed to make it easier to
search for them in the future, and can be deleted permanently if desired.
For consistency in handling tickets, your staff team should devise a procedure
and adhere to it.

If the owner leaves or is removed from their ticket, the bot will automatically
archive the ticket. Staff are free to re-open it afterwards.
The bot will also lock the ticket to prevent further discussion if it has
the Manage Threads permission, which can be set on a per-channel basis.

Note that if you have multiple inboxes in one channel, any staff with the
Manage Threads permission will be able to view and manage all threads in
that channel, even if they aren't listed as staff for that inbox.
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

Alternatively, you can choose to not grant the Manage Threads permission
to staff. This will prevent them from being able to invite other members.
You can still manually edit a thread to allow anyone to invite members,
but this also applies to the ticket owner which may not be desired.
For now, you cannot change the default invite behaviour for new tickets.

## Customization

There are various settings that can be customized for each inbox.
When you use the below commands, you will be prompted to select the message
of the inbox that you want to change, i.e. the message that has the
Create Ticket button.

- `/inbox message`

  Edit the message of an inbox with another message.

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

  To keep push notifications easy to understand at a glance, make sure the
  starter message says something unique to its inbox at the beginning, like:

  ```
  $author Thank you for creating a moderation ticket! $staff will be with you shortly.
  ```

  Note that role mentions require either the role to be mentionable or the bot
  to have the *Mention all roles* permission in the inbox's channel.

- `/inbox new-tickets name`

  Inspect the default name for new tickets and optionally change it.

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

  Note that thread names are limited to 100 characters by Discord.

## Ticket Limits

Each inbox has a per-user ratelimit to help reduce spam. It adjusts according
to the slowmode you have set for the inbox's channel, but the minimum time
allowed between tickets is 60 seconds. Inboxes also try to maintain a maximum
of 1 active thread per user, although it is not guaranteed due to technical
limitations.

## Encryption

> [!WARNING]
>
> This feature is experimental and may be removed in the future.
>
> Currently, derived keys are not cached by the bot, meaning that every connection
> made to the database, which can be several connections per command, requires
> repeating the same key derivation which may be performance intensive.
>
> Encryption is also not a substitute for properly configured file permissions.
> You should ensure that other users on your system are not able to read the
> database or the config.toml file. Other secure methods of transferring
> these files between systems should be applied as well.
>
> Also, it's worth noting that this bot avoids storing any sensitive data
> on users and only persists the bare minimum needed to function.
> Primary concerns should be preventing your bot token from being leaked.

This bot supports using an encrypted SQLite database with encryption extensions
like [SQLiteMultipleCiphers], [SQLCipher], or [SEE]. On a Windows system,
pre-built DLLs can be found for SQLiteMultipleCiphers in their
[releases](https://github.com/utelle/SQLite3MultipleCiphers/releases) page.

With one of the encryption extensions installed, you can use it to encrypt
the database and then add the decryption to theticketbot. Run the bot once
so `data/theticketbot.db` is created (or whatever path you set it to), then
open the database using the SQLite shell from your encryption extension
and encrypt it:

```sql
$ sqlite3 data/theticketbot.db
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
# NOTE: when first encrypting with hexkey, use hexrekey instead of rekey
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

[MIT]: /LICENSE
