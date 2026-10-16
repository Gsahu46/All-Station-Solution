-- Challenge 2: who did it.
ALTER TABLE audit_events ADD COLUMN actor VARCHAR(40) NOT NULL DEFAULT 'system';
ALTER TABLE audit_events ADD CONSTRAINT audit_events_actor_not_blank CHECK (btrim(actor) <> '');
