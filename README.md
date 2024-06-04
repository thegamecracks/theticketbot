# theticketbot

A simple Discord bot for handling ticket systems using channel threads.

![](/docs/images/demo.png)

## Contributing

Want to help out by adding translations? [Fork this repository],
create a new branch, commit your PO files there, and make a pull request!
See [discord.py-gettext-demo's onboarding] for more information.

[Fork this repository]: https://docs.github.com/en/get-started/quickstart/contributing-to-projects
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
   python -m theticketbot
   ```

5. Invite your bot to a server and use "<@mention> sync" to synchronize
   the bot's application commands.

[config.toml]: /src/theticketbot/config_default.toml

To set up an inbox, first post a message with the content you would like your
inbox message to have. This message may include image attachments, or custom
embeds sent by a webhook as long as the message has no content.

Afterwards, right-click or long tap the message, open the Apps menu, and use
the command `Select this message`. For a short period of time, you can use
`/inbox create` to select a channel to post the inbox. The bot must be able
to view, send messages, and create private threads in that channel.
Currently, there are no limits on the number of inboxes your server can have.

Tickets are managed just like threads. Closing them archives the thread,
preserving their messages without needing a separate transcript. Staff with
`MANAGE_THREADS` permissions can also add and remove members afterwards,
useful for bringing in relevant members or for privating the thread to
continue internal discussions. Tickets can be renamed to make it easier to
search for them in the future, and can be deleted permanently if desired.
For consistency in handling tickets, your staff team should devise a procedure
and adhere to it.

If the owner leaves or is removed from their ticket, the bot will automatically
archive the ticket. Staff are free to re-open it afterwards.

## Customization

There are various settings that can be customized for each inbox.
Before you can use the below commands, you must first select an inbox,
i.e. the message that has the Create Ticket button.

- `/inbox staff add <staff>`

  Add members or roles to be considered staff for an inbox.

- `/inbox new-tickets set-starter`

  Inspect the starting message for new tickets and optionally change it.

  Allowed placeholders are:

  - `$author`

    The ticket owner's mention. Must be included in the message
    for the owner to be invited.

  - `$staff`

    A comma-separated list of mentions for the inbox's staff members
    and roles. Must be included in the message for staff to be invited
    if they do not have the Manage Threads permission.

  To keep push notifications easy to understand at a glance, make sure the
  starter message says something unique to its inbox at the beginning, like:

  ```
  $author Thank you for creating a moderation ticket! $staff will be with you shortly.
  ```

  Note that role mentions require either the role to be mentionable or the bot
  to have the *Mention all roles* permission in the inbox's channel.

- `/inbox new-tickets set-ticket-name`

  Inspect the default name for new tickets and optionally change it.

  Allowed placeholders are:

  - `$year`
  - `$month`
  - `$day`
  - `$name`

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

## License

This project is written under the [MIT] license.

[MIT]: /LICENSE
