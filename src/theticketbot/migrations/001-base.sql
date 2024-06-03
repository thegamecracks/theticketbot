CREATE TABLE user (id INTEGER PRIMARY KEY);
CREATE TABLE guild (id INTEGER PRIMARY KEY);

CREATE TABLE member (
    guild_id
        INTEGER
        REFERENCES guild (id) ON DELETE CASCADE,
    user_id
        INTEGER
        REFERENCES user (id) ON DELETE CASCADE,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE channel (
    id INTEGER PRIMARY KEY,
    guild_id
        INTEGER
        REFERENCES guild (id) ON DELETE CASCADE
);

CREATE TABLE message (
    id INTEGER PRIMARY KEY,
    channel_id
        INTEGER NOT NULL
        REFERENCES channel (id) ON DELETE CASCADE
);

CREATE TABLE inbox (
    id
        INTEGER PRIMARY KEY
        REFERENCES message (id) ON DELETE CASCADE,
    starter_content TEXT NOT NULL DEFAULT '',
    max_tickets_per_user INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE inbox_staff (
    inbox_id
        INTEGER
        REFERENCES inbox (id) ON DELETE CASCADE,
    mention TEXT NOT NULL, -- CHECK mention REGEXP '<@\d+>|<@&\d+>'
    PRIMARY KEY (inbox_id, mention)
);

CREATE TABLE ticket (
    id
        INTEGER PRIMARY KEY
        REFERENCES channel (id) ON DELETE CASCADE,

    inbox_id INTEGER REFERENCES inbox (id) ON DELETE SET NULL,
    owner_id INTEGER REFERENCES user (id) ON DELETE SET NULL

    -- The following invariants are not checked:
    --   * channel.guild == inbox.message.channel.guild
    --   * owner has a corresponding member row
);

-- Optimize counting a user's tickets in an inbox
CREATE INDEX ix_ticket_inbox_owner ON ticket (inbox_id, owner_id);

-- Optimize cascading foreign keys
CREATE INDEX ix_member_user ON member (user_id);
CREATE INDEX ix_channel_guild ON channel (guild_id);
CREATE INDEX ix_message_channel ON message (channel_id);
