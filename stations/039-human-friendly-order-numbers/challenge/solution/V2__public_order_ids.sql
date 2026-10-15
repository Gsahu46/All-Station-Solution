-- A random public id for apps and links: unguessable, unlike the readable number. gen_random_uuid() is built in
-- since PostgreSQL 13; existing rows get one too.
ALTER TABLE orders ADD COLUMN public_id UUID NOT NULL DEFAULT gen_random_uuid();
ALTER TABLE orders ADD CONSTRAINT orders_public_id_unique UNIQUE (public_id);
