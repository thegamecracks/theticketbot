# Concept

A ticket bot allows communities to start private conversations with staff,
often to get support with something.

Unlike a typical ticket bot which creates and deletes text channels,
the goal of this project is using channel threads which natively supports
private visibility, inviting members, and archival.

## Usage

Users should be able to click a button on a message to create a private thread
in that channel. Once created, a custom message is sent and the user is invited
to the thread along with specific roles or members. The staff, and optionally
the user, should be able to close the thread at any time.

## Configuration

A server admin should be able to:

- Create a ticket inbox in an existing channel
  - Guild/channel permissions should be validated
    - Create Private Threads
    - Send Messages in Threads
  - Multiple ticket inboxes should be allowed in the same channel
- Select a message to use for content
  - Could be more sophisticated but this is simple to implement
- Configure a ticket inbox's maximum number of tickets per member

The following configuration can be hardcoded:

- Maximum ticket inboxes per guild
- Ticket inbox ratelimit (60s per inbox, per member)
