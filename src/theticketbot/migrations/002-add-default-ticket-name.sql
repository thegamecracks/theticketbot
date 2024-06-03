ALTER TABLE inbox
    ADD COLUMN
        default_ticket_name TEXT NOT NULL DEFAULT '';
