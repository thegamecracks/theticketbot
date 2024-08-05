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

command-select = Diese Nachricht auswählen

# NOTE: alternatively translated as panel
command-inbox = panel
    .description = Verwalten Sie die Ticket-Panels des Servers.

# TODO
command-inbox-create = erstelle
    .description = Erstellen Sie ein neues Panel.
    .channel-name = kanal
    .channel-description = Der Kanal, in dem das Panel gepostet wird.
    .destination-name = destination
    .destination-description = The channel to route new tickets.

# TODO
command-inbox-destination = destination
    .description = Edit the destination channel for an inbox.
    .channel-name = channel
    .channel-description = The channel to route new tickets.

command-inbox-message = nachricht
    .description = Bearbeiten Sie die Nachricht für ein Panel.

command-inbox-staff = teammitglieder
    .description = Verwalten Sie die Teammitglieder für ein Panel.

command-inbox-new-tickets = neue-tickets
    .description = Verwalten Sie neue Tickets, die von einem Panel erstellt wurden.

command-inbox-new-tickets-starter = startnachricht
    .description = Legen Sie die Startnachricht für neue Tickets fest.

command-inbox-new-tickets-name = name
    .description = Legen Sie den Namen für neue Tickets fest.

## Error handling

# Message appended to some error responses caused by issues in the bot
#       { $code }: The error code to be reported
# { $maintainer }: The maintainer's mention
error-trailer =
    Fehlercode: { $code }
    Wenn Sie Hilfe benötigen, wenden Sie sich bitte an { $maintainer }.

# Error response for command on cooldown
# { $duration }: The duration to wait in seconds
error-command-on-cooldown =
    Dieser Befehl hat eine Abklingzeit von { NUMBER($duration, maximumFractionDigits: 1) }s.

# Error response for exceeding maximum concurrent users of a command
error-max-concurrency = Zu viele Personen verwenden diesen Befehl im Moment. Bitte versuchen Sie es später noch einmal.

# Error response for not passing all checks required to use a command
error-check-failure = Eine oder mehrere Prüfungen für diesen Befehl sind fehlgeschlagen.

# Error response for failing to parse the user's input
# { $description }: The error's description
error-user-input =
    Bei Ihrer Eingabe ist ein Fehler aufgetreten: ```py
    { $description }```

# Error response for an unexpected failure in a command
error-unknown = Bei der Ausführung des Befehls ist ein unbekannter Fehler aufgetreten.

# Error response for using a slash command not recognized by the bot
error-command-not-found = Der Bot erkennt diesen Befehl derzeit nicht.

## Select cog

# Message sent when selecting a message without a command
select-no-command = Sie können im Moment keine Nachricht auswählen! Bitte verwenden Sie zuerst einen Befehl, der nach einer Nachricht fragt.

# Message sent when selecting a message too long after their last command
select-expired = Entschuldigung, Ihr letzter Befehl ist abgelaufen. Bitte verwenden Sie erneut einen Befehl und wählen Sie dann diese Nachricht aus.

## Inbox cog

# Message sent when selecting a non-inbox message
# that looks like the message used to be an inbox
# { $message }: The message's link
select-unknown-inbox = Entschuldigung, { $message } wird nicht mehr als Panel erkannt und muss neu erstellt werden.

# Message sent when selecting a non-inbox message
# { $message }: The message's link
select-invalid-inbox = Entschuldigung, { $message } ist kein Panel. Die von Ihnen ausgewählte Nachricht sollte eine Schaltfläche **{ inbox-ticket-button }** darunter haben.

# Message sent when attempting to create an inbox with insufficient permissions
#     { $channel }: The channel's mention
# { $permissions }: A list of permissions that are missing
inbox-create-insufficient-permissions = Ich benötige die folgenden Berechtigungen in { $channel }: { $permissions }

# TODO Your inbox will be posted in { $channel } and tickets will be created in { $destination }. You must now select the message you want your inbox to have. To do this, right click or long tap a message, then open Apps and pick the *{ command-select }* command.
# Message sent when the user is creating a new inbox in a channel,
# and the inbox needs a message to be included
#     { $channel }: The channel's mention
# { $destination }: The destination's mention
inbox-create-with-message = Der Kanal { $channel } wurde als Ziel für Ihr neues Panel festgelegt. Sie müssen nun die Nachricht auswählen, die Ihr Panel haben soll. Klicken Sie dazu mit der rechten Maustaste auf eine Nachricht oder drücken Sie lange auf eine Nachricht, öffnen Sie dann Apps und wählen Sie den Befehl *{ command-select }*.

# The default starter message content for new tickets
# $author: The author's mention
#  $staff: A list of staff mentions
ticket-starter-message-content =
    $author Danke, dass Sie ein Ticket erstellt haben!
    $staff

# Message sent after a user creates an inbox
# { $inbox }: The inbox's link
inbox-create-finished = Ihr Panel wurde erstellt! { $inbox }

# Message sent when attempting to create an inbox with too large attachments
# { $filesize }: The maximum cumulative filesize
inbox-create-oversized-attachments = Die Anhänge der Nachricht sind zu groß! Die Gesamtgröße muss unter { $filesize } liegen.

# Message sent when a user needs to select an inbox to edit
select-inbox-to-edit = Sie müssen nun das Panel auswählen, das Sie bearbeiten möchten. Klicken Sie dazu mit der rechten Maustaste auf eine Nachricht oder drücken Sie lange auf eine Nachricht, öffnen Sie dann Apps und wählen Sie den Befehl *{ command-select }*.

# TODO
# Message sent when an inbox's old and new destination are the same
#       { $inbox }: The inbox's link
# { $destination }: The destination's link
inbox-destination-matches = { $inbox } is already routing tickets to { $destination } !

# TODO
# Message sent after a user edits an inbox's destination
# { $inbox }: The inbox's link
#   { $old }: The old destination's link
#   { $new }: The new destination's link
inbox-destination-changed = { $inbox } will now route tickets to { $new } instead of { $old } !

# Message sent when a user is editing an inbox's message,
# and a second message needs to be selected to copy its contents
# { $inbox }: The inbox's link
inbox-message-select = { $inbox } wird bearbeitet. Bitte wählen Sie die Nachricht aus, die Sie kopieren möchten.

# Message sent when a user tries to edit an inbox message with itself
inbox-message-selected-self = Die Panelmeldung kann nicht mit sich selbst bearbeitet werden. Bitte wählen Sie eine andere Nachricht aus, die Sie kopieren möchten.

# Message sent after a user edits an inbox's message
# { $inbox }: The inbox's link
inbox-message-finished = { $inbox } wurde aktualisiert!

# Message sent when a user is managing staff for an inbox,
# and an inbox needs to be selected
select-inbox-to-edit-staff = Sie müssen nun das Panel auswählen, für das Sie Teammitglieder verwalten möchten. Klicken Sie dazu mit der rechten Maustaste auf eine Nachricht oder drücken Sie lange darauf, öffnen Sie Apps und wählen Sie den Befehl *{ command-select }*.

# Message sent above select menus when presenting an inbox's staff
# { $inbox }: The inbox's link
inbox-staff-message = Teammitglieder für { $inbox } :

# Message sent when submitting no changes to inbox staff
inbox-staff-no-edits = Sie haben keine Änderungen vorgenommen!

# Message sent when a user leaves their ticket
# { $owner }: The ticket owner's mention
ticket-archived-owner-left = Ticket wird archiviert, da der Besitzer ({ $owner }) den Thread verlassen hat.

# Message sent when a user leaves a server with open tickets
# { $owner }: The ticket owner's mention
ticket-archived-owner-left-guild = Ticket wird archiviert, da der Besitzer ({ $owner }) den Server verlassen hat.

# Message sent when locking a thread after being archived
ticket-archived-lock = Dieses archivierte Ticket wird für alle außer Moderatoren gesperrt.

# Modal for changing an inbox's starter message
# .content: Text input label
modal-starter = Startnachricht
    .content = Inhalt

# Message sent when an inbox's starter message is successfully changed
# { $inbox }: The inbox's link
modal-starter-finished = Die Startnachricht von { $inbox } wurde festgelegt!

# Modal for changing an inbox's defaults for new tickets
# .name: Text input label
modal-new-tickets = Neue Tickets
    .name = Name

# Message sent when an inbox's ticket defaults were successfully changed
# { $inbox }: The inbox's link
inbox-new-tickets-finished = Die Standardeinstellungen von { $inbox } wurden festgelegt!

# Button label for creating a new ticket
inbox-ticket-button = Ticket erstellen

# Message sent when an inbox is not recognized
inbox-ticket-unknown = Entschuldigung, dieses Panel wird nicht mehr erkannt und muss neu erstellt werden. Bitte benachrichtigen Sie einen Server-Administrator!

# Message sent when trying to create too many tickets
# { $ticket }: The ticket's link
inbox-ticket-max-per-user = Sie haben zu viele Tickets in diesem Panel. Bitte schließen Sie Ihr letztes Ticket { $ticket } , bevor Sie ein neues erstellen.

# Message sent when user is being ratelimited for an inbox
# { $duration }: The duration in seconds to wait before retrying
inbox-ticket-on-cooldown = Sie erstellen Ihre Tickets zu schnell! Bitte warten Sie { NUMBER($duration, maximumFractionDigits: 0) }s.

# Message sent when creating a ticket
inbox-ticket-creating = Erstelle Ticket...

# Audit log reason for a user creating a ticket
# { $owner }: The ticket owner's name
inbox-ticket-creating-reason = Ticket wurde von { $owner } erstellt

# Message sent when creating a ticket failed due to insufficient permissions
inbox-ticket-error-insufficient-bot-permissions = Ich habe nicht die nötigen Rechte, um hier ein Ticket zu erstellen. Bitte benachrichtigen Sie einen Server-Administrator!

# Message sent when creating a ticket failed unexpectedly
inbox-ticket-error-unknown = Beim Erstellen des Tickets ist ein unerwarteter Fehler aufgetreten.

# Message sent after successfully creating a ticket
# { $ticket }: the ticket's link
inbox-ticket-finished = Ihr Ticket ist bereit! { $ticket }
