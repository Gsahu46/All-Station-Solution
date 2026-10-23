-- How many orders an export sent, filled in when its last row is written (empty while it runs, or if it was cut off).
ALTER TABLE export_log ADD COLUMN rows_sent integer;
ALTER TABLE export_log ADD CONSTRAINT export_log_rows_sent CHECK (rows_sent >= 0);
