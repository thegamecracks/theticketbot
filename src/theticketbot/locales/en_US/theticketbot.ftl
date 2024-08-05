### theticketbot
### Copyright (C) 2024 thegamecracks
### This file is distributed under the same license as the theticketbot package.
###
### The following requirements must be met when providing translations for
### certain strings:
###
### * Command name
### * Command group name
### * Command parameter name
### * Subcommand name
### * Subcommand group name
### * Subcommand parameter name
###   - Lowercase variants of characters must be used
###   - No spaces allowed, use "-" or "_" instead ("-" is preferred)
###   - Max length of 32 characters
###
### * Command description
### * Command group description
### * Command parameter description
### * Subcommand description
### * Subcommand group description
### * Subcommand parameter description
###   - Max length of 100 characters
###
### Note that if any placeholders are described as "links", avoid placing
### non-whitespace characters around them, like punctuation. This can break
### the link and/or cause it to be incorrectly embedded by Discord.

## Application commands

command-select = Select this message

# NOTE: alternatively translated as panel
command-inbox = inbox
    .description = Manage the server's ticket inboxes.

command-inbox-create = create
    .description = Create a new inbox.
    .channel-name = channel
    .channel-description = The channel to post the inbox.
    .destination-name = destination
    .destination-description = The channel to route new tickets.

command-inbox-destination = destination
    .description = Edit the destination channel for an inbox.
    .channel-name = channel
    .channel-description = The channel to route new tickets.

command-inbox-message = message
    .description = Edit the message for an inbox.

command-inbox-staff = staff
    .description = Manage staff for an inbox.

command-inbox-new-tickets = new-tickets
    .description = Manage new tickets created by an inbox.

command-inbox-new-tickets-starter = starter
    .description = Set the starting message for new tickets.

command-inbox-new-tickets-name = name
    .description = Set the name for new tickets.

## Error handling

# Message appended to some error responses caused by issues in the bot
#       { $code }: The error code to be reported
# { $maintainer }: The maintainer's mention
error-trailer =
    Error code: { $code }
    If assistance is needed, please contact { $maintainer }.

# Error response for command on cooldown
# { $duration }: The duration to wait in seconds
error-command-on-cooldown =
    This command is on cooldown for { NUMBER($duration, maximumFractionDigits: 1) }s.

# Error response for exceeding maximum concurrent users of a command
error-max-concurrency = Too many people are using this command. Please try again later.

# Error response for not passing all checks required to use a command
error-check-failure = One or more checks failed for this command.

# Error response for failing to parse the user's input
# { $description }: The error's description
error-user-input =
    An error occurred with your input: ```py
    { $description }```

# Error response for an unexpected failure in a command
error-unknown = An unknown error occurred while running this command.

# Error response for using a slash command not recognized by the bot
error-command-not-found = The bot currently does not recognize this command.

## Select cog

# Message sent when selecting a message without a command
select-no-command = You can't select a message right now! Please use a command that asks for a message first.

# Message sent when selecting a message too long after their last command
select-expired = Sorry, your last command has expired. Please use a command again and then select this message.

## Inbox cog

# Message sent when selecting a non-inbox message
# that looks like the message used to be an inbox
# { $message }: The message's link
select-unknown-inbox = Sorry, { $message } is no longer recognized as an inbox and must be re-created.

# Message sent when selecting a non-inbox message
# { $message }: The message's link
select-invalid-inbox = Sorry, { $message } is not an inbox. The message you select should have a **{ inbox-ticket-button }** button under it.

# Message sent when attempting to create an inbox with insufficient permissions
#     { $channel }: The channel's mention
# { $permissions }: A list of permissions that are missing
inbox-create-insufficient-permissions = I need the following permissions in { $channel }: { $permissions }

# Message sent when the user is creating a new inbox in a channel,
# and the inbox needs a message to be included
#     { $channel }: The channel's mention
# { $destination }: The destination's mention
inbox-create-with-message = Your inbox will be posted in { $channel } and tickets will be created in { $destination }. You must now select the message you want your inbox to have. To do this, right click or long tap a message, then open Apps and pick the *{ command-select }* command.

# The default starter message content for new tickets
# $author: The author's mention
#  $staff: A list of staff mentions
ticket-starter-message-content =
    $author Thank you for creating a ticket!
    $staff

# Message sent after a user creates an inbox
# { $inbox }: The inbox's link
inbox-create-finished = Your inbox has been created! { $inbox }

# Message sent when attempting to create an inbox with too large attachments
# { $filesize }: The maximum cumulative filesize
inbox-create-oversized-attachments = The message's attachments are too large! The total size must be under { $filesize }.

# Message sent when a user needs to select an inbox to edit
select-inbox-to-edit = You must now select the inbox you want to edit. To do this, right click or long tap a message, then open Apps and pick the *{ command-select }* command.

# Message sent when an inbox's old and new destination are the same
#       { $inbox }: The inbox's link
# { $destination }: The destination's link
inbox-destination-matches = { $inbox } is already routing tickets to { $destination } !

# Message sent after a user edits an inbox's destination
# { $inbox }: The inbox's link
#   { $old }: The old destination's link
#   { $new }: The new destination's link
inbox-destination-changed = { $inbox } will now route tickets to { $new } instead of { $old } !

# Message sent when a user is editing an inbox's message,
# and a second message needs to be selected to copy its contents
# { $inbox }: The inbox's link
inbox-message-select = { $inbox } will be edited. Please select the message you want to copy.

# Message sent when a user tries to edit an inbox message with itself
inbox-message-selected-self = The inbox message cannot be edited with itself. Please select another message you want to copy.

# Message sent after a user edits an inbox's message
# { $inbox }: The inbox's link
inbox-message-finished = { $inbox } has been updated!

# Message sent when a user is managing staff for an inbox,
# and an inbox needs to be selected
select-inbox-to-edit-staff = You must now select the inbox you want to manage staff for. To do this, right click or long tap a message, then open Apps and pick the *{ command-select }* command.

# Message sent above select menus when presenting an inbox's staff
# { $inbox }: The inbox's link
inbox-staff-message = Staff for { $inbox } :

# Message sent when submitting no changes to inbox staff
inbox-staff-no-edits = You have not made any changes!

# Message sent when a user leaves their ticket
# { $owner }: The ticket owner's mention
ticket-archived-owner-left = Archiving ticket as the owner ({ $owner }) has left the thread.

# Message sent when a user leaves a server with open tickets
# { $owner }: The ticket owner's mention
ticket-archived-owner-left-guild = Archiving ticket as the owner ({ $owner }) has left the server.

# Message sent when locking a thread after being archived
ticket-archived-lock = This archived ticket will be locked to moderators only.

# Modal for changing an inbox's starter message
# .content: Text input label
modal-starter = Starter Message
    .content = Content

# Message sent when an inbox's starter message is successfully changed
# { $inbox }: The inbox's link
modal-starter-finished = { $inbox } 's starting message has been set!

# Modal for changing an inbox's defaults for new tickets
# .name: Text input label
modal-new-tickets = New Tickets
    .name = Name

# Message sent when an inbox's ticket defaults were successfully changed
# { $inbox }: The inbox's link
inbox-new-tickets-finished = { $inbox } 's ticket defaults have been set!

# Button label for creating a new ticket
inbox-ticket-button = Create Ticket

# Message sent when an inbox is not recognized
inbox-ticket-unknown = Sorry, this inbox is no longer recognized and must be re-created. Please notify a server admin!

# Message sent when trying to create too many tickets
# { $ticket }: The ticket's link
inbox-ticket-max-per-user = You have too many tickets in this inbox. Please close your last ticket { $ticket } before creating a new one.

# Message sent when user is being ratelimited for an inbox
# { $duration }: The duration in seconds to wait before retrying
inbox-ticket-on-cooldown = You are creating tickets too quickly! Please wait { NUMBER($duration, maximumFractionDigits: 0) }s.

# Message sent when creating a ticket
inbox-ticket-creating = Creating ticket...

# Audit log reason for a user creating a ticket
# { $owner }: The ticket owner's name
inbox-ticket-creating-reason = Ticket created by { $owner }

# Message sent when creating a ticket failed due to insufficient permissions
inbox-ticket-error-insufficient-bot-permissions = I am missing the permissions needed to create a ticket here. Please notify a server admin!

# Message sent when creating a ticket failed unexpectedly
inbox-ticket-error-unknown = An unexpected error occurred while creating the ticket.

# Message sent after successfully creating a ticket
# { $ticket }: the ticket's link
inbox-ticket-finished = Your ticket is ready! { $ticket }
