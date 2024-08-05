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

command-select = Sélectionner ce message

# NOTE: alternatively translated as panel
command-inbox = panel
    .description = Gérer les panels de tickets du serveur.

# TODO
command-inbox-create = créer
    .description = Créer un nouveau panel.
    .channel-name = canal
    .channel-description = Le canal où poster le panel.
    .destination-name = destination
    .destination-description = The channel to route new tickets.

# TODO
command-inbox-destination = destination
    .description = Edit the destination channel for an inbox.
    .channel-name = channel
    .channel-description = The channel to route new tickets.

command-inbox-message = message
    .description = Édition du message pour un panel.

command-inbox-staff = équipe
    .description = Gérer l'équipe associée à un panel.

command-inbox-new-tickets = nouveaux-tickets
    .description = Gérer les nouveaux tickets créés par un panel.

command-inbox-new-tickets-starter = démarrer
    .description = Choisir le message de démarrage pour les nouveaux tickets.

command-inbox-new-tickets-name = nom
    .description = Sélectionner le nom pour les nouveaux tickets.

## Error handling

# Message appended to some error responses caused by issues in the bot
#       { $code }: The error code to be reported
# { $maintainer }: The maintainer's mention
error-trailer =
    Erreur, code: { $code }
    Si vous avez besoin de support, merci de contacter { $maintainer }.

# Error response for command on cooldown
# { $duration }: The duration to wait in seconds
error-command-on-cooldown =
    Cette commande est temporairement inactive pour { NUMBER($duration, maximumFractionDigits: 1) }s.

# Error response for exceeding maximum concurrent users of a command
error-max-concurrency = Un trop grand nombre d'utilisateurs font usage de cette commande. Veuillez réessayer plus tard.

# Error response for not passing all checks required to use a command
error-check-failure = Une ou plusieurs vérifications ont échoué pour cette commande.

# Error response for failing to parse the user's input
# { $description }: The error's description
error-user-input =
    Une erreur s'est produite avec l'entrée: ```py
    { $description }```

# Error response for an unexpected failure in a command
error-unknown = Une erreur inconnue s'est produite en exécutant cette commande.

# Error response for using a slash command not recognized by the bot
error-command-not-found = Le robot ne reconnaît pas pour le moment cette commande.

## Select cog

# Message sent when selecting a message without a command
select-no-command = Vous ne pouvez pas sélectionner un message pour le moment ! Merci d'utiliser une commande qui demande un message en premier.

# Message sent when selecting a message too long after their last command
select-expired = Désolé, votre dernière commande a expiré. Merci d'utiliser une commande à nouveau et de sélectionner ce message.

## Inbox cog

# Message sent when selecting a non-inbox message
# that looks like the message used to be an inbox
# { $message }: The message's link
select-unknown-inbox = Désolé, { $message } n'est plus reconnu comme un panel et doit être recréé.

# Message sent when selecting a non-inbox message
# { $message }: The message's link
select-invalid-inbox = Désolé, { $message } n'est pas un panel. Le message que vous sélectionnez doit avoir un bouton **{ inbox-ticket-button }** en dessous.

# Message sent when attempting to create an inbox with insufficient permissions
#     { $channel }: The channel's mention
# { $permissions }: A list of permissions that are missing
inbox-create-insufficient-permissions = Vous avez besoin des permissions suivantes dans { $channel }: { $permissions }

# TODO Your inbox will be posted in { $channel } and tickets will be created in { $destination }. You must now select the message you want your inbox to have. To do this, right click or long tap a message, then open Apps and pick the *{ command-select }* command.
# Message sent when the user is creating a new inbox in a channel,
# and the inbox needs a message to be included
#     { $channel }: The channel's mention
# { $destination }: The destination's mention
inbox-create-with-message = Le canal { $channel } a été défini comme destination pour votre nouveau panel. Vous devez maintenant sélectionner le message que vous souhaitez que votre panel ait. Pour ce faire, cliquez (bouton droit) ou appuyez longuement sur un message, puis ouvrez les applications et choisissez la commande *{ command-select }*.

# The default starter message content for new tickets
# $author: The author's mention
#  $staff: A list of staff mentions
ticket-starter-message-content =
    $author : Merci de créer un ticket !
    $staff

# Message sent after a user creates an inbox
# { $inbox }: The inbox's link
inbox-create-finished = Votre panel a été créée ! { $inbox }

# Message sent when attempting to create an inbox with too large attachments
# { $filesize }: The maximum cumulative filesize
inbox-create-oversized-attachments = Le fichier joint est trop volumineux ! La taille totale doit être inférieure à { $filesize }.

# Message sent when a user needs to select an inbox to edit
select-inbox-to-edit = Vous devez maintenant sélectionner le panel que vous souhaitez éditer. Pour ce faire, cliquez (bouton droit) ou appuyez longuement sur un message, puis ouvrez les applications et choisissez la commande *{ command-select }*.

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
inbox-message-select = { $inbox } sera édité. Veuillez sélectionner le message que vous souhaitez copier.

# Message sent when a user tries to edit an inbox message with itself
inbox-message-selected-self = Le message ne peut pas être édité avec lui-même. Veuillez sélectionner un autre message que vous souhaitez copier.

# Message sent after a user edits an inbox's message
# { $inbox }: The inbox's link
inbox-message-finished = { $inbox } a été mis à jour !

# Message sent when a user is managing staff for an inbox,
# and an inbox needs to be selected
select-inbox-to-edit-staff = Vous devez maintenant sélectionner le panel pour lequel vous souhaitez gérer l'équipe. Pour ce faire, cliquez (bouton droit) ou appuyez longuement sur un message, puis ouvrez les applications et choisissez la commande *{ command-select }*.

# Message sent above select menus when presenting an inbox's staff
# { $inbox }: The inbox's link
inbox-staff-message = Équipe pour { $inbox } :

# Message sent when submitting no changes to inbox staff
inbox-staff-no-edits = Vous n'avez effectué aucune modification !

# Message sent when a user leaves their ticket
# { $owner }: The ticket owner's mention
ticket-archived-owner-left = Archivage du ticket car le propriétaire ({ $owner }) a quitté le fil.

# Message sent when a user leaves a server with open tickets
# { $owner }: The ticket owner's mention
ticket-archived-owner-left-guild = Archivage du ticket car le propriétaire ({ $owner }) a quitté le serveur.

# Message sent when locking a thread after being archived
ticket-archived-lock = Ce ticket archivé sera verrouillé pour les modérateurs uniquement.

# Modal for changing an inbox's starter message
# .content: Text input label
modal-starter = Message d'introduction
    .content = Contenu

# Message sent when an inbox's starter message is successfully changed
# { $inbox }: The inbox's link
modal-starter-finished = Le message d'introduction de { $inbox } a été défini !

# Modal for changing an inbox's defaults for new tickets
# .name: Text input label
modal-new-tickets = Nouveau tickets
    .name = Nom

# Message sent when an inbox's ticket defaults were successfully changed
# { $inbox }: The inbox's link
inbox-new-tickets-finished = Le ticket par défaut de { $inbox } a été défini !

# Button label for creating a new ticket
inbox-ticket-button = Créer un ticket

# Message sent when an inbox is not recognized
inbox-ticket-unknown = Désolé, ce panel n'est plus reconnu et doit être recrée. Veuillez contacter un administrateur !

# Message sent when trying to create too many tickets
# { $ticket }: The ticket's link
inbox-ticket-max-per-user = Vous avez trop de tickets dans cette boîte. Merci de clôturer votre ticket  { $ticket } avant d'en créer un nouveau.

# Message sent when user is being ratelimited for an inbox
# { $duration }: The duration in seconds to wait before retrying
inbox-ticket-on-cooldown = Vous créez des tickets trop rapidement ! Merci d'attendre { NUMBER($duration, maximumFractionDigits: 0) }s.

# Message sent when creating a ticket
inbox-ticket-creating = Création du ticket...

# Audit log reason for a user creating a ticket
# { $owner }: The ticket owner's name
inbox-ticket-creating-reason = Ticket crée par { $owner }

# Message sent when creating a ticket failed due to insufficient permissions
inbox-ticket-error-insufficient-bot-permissions = Vous n'avez pas les permissions nécessaires pour créer un ticket ici. Merci de notifier unadministrateur du serveur !

# Message sent when creating a ticket failed unexpectedly
inbox-ticket-error-unknown = Une erreur inconnue s'est produite lors de la création du ticket.

# Message sent after successfully creating a ticket
# { $ticket }: the ticket's link
inbox-ticket-finished = Votre ticket est prêt ! { $ticket }
