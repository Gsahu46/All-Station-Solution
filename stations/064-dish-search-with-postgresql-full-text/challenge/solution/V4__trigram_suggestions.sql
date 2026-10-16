-- Challenge 2: trigram similarity ("panner" shares most three-letter pieces with "paneer"), with its own index.
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX dishes_name_trigram ON dishes USING GIN (lower(name) gin_trgm_ops);
