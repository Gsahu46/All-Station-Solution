-- An adjacency list: each category names its parent. Moving a category is one UPDATE; nothing else stores its path.
CREATE TABLE categories (
    id        BIGINT       PRIMARY KEY,
    parent_id BIGINT       CONSTRAINT categories_parent_fk REFERENCES categories (id),
    name      VARCHAR(60)  NOT NULL,
    slug      VARCHAR(60)  NOT NULL CONSTRAINT categories_slug_shape CHECK (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
    CONSTRAINT categories_not_own_parent CHECK (parent_id <> id),
    CONSTRAINT categories_slug_per_parent UNIQUE NULLS NOT DISTINCT (parent_id, slug)
);
CREATE INDEX categories_parent ON categories (parent_id);

-- No category may sit under one of its own descendants: that would be a loop with no root.
-- The advisory lock makes moves take turns, so two moves at once cannot build a loop between them.
CREATE FUNCTION categories_no_cycle() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.parent_id IS NOT NULL THEN
        PERFORM pg_advisory_xact_lock(hashtext('categories_tree'));
        IF EXISTS (WITH RECURSIVE up AS (
                       SELECT id, parent_id FROM categories WHERE id = NEW.parent_id
                       UNION ALL
                       SELECT c.id, c.parent_id FROM categories c JOIN up ON c.id = up.parent_id)
                   SELECT 1 FROM up WHERE id = NEW.id) THEN
            RAISE EXCEPTION 'categories_no_cycle: category % cannot move under its own descendant %', NEW.id, NEW.parent_id
                USING ERRCODE = 'check_violation';
        END IF;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER categories_no_cycle BEFORE INSERT OR UPDATE OF parent_id ON categories
    FOR EACH ROW EXECUTE FUNCTION categories_no_cycle();
