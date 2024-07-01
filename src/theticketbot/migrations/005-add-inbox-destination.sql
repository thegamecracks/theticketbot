ALTER TABLE inbox
    ADD COLUMN
        destination_id INTEGER REFERENCES channel (id) ON DELETE SET NULL;
