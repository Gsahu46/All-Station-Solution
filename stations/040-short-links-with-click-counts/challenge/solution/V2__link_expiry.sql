-- Optional end of a link's life. NULL: it never expires.
ALTER TABLE links ADD COLUMN expires_at TIMESTAMPTZ;
