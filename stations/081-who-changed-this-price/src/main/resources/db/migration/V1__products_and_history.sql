CREATE TABLE products (
    id          bigint CONSTRAINT products_pk PRIMARY KEY,
    seller      text NOT NULL,
    name        text NOT NULL,
    price_paise bigint NOT NULL,
    CONSTRAINT products_price_positive CHECK (price_paise > 0),
    CONSTRAINT products_name_length CHECK (char_length(name) BETWEEN 1 AND 120)
);

-- One row per change set (Hibernate Envers' revision entity): when, and who, taken from the signed-in user.
CREATE TABLE revisions (
    id            bigint GENERATED ALWAYS AS IDENTITY CONSTRAINT revisions_pk PRIMARY KEY,
    changed_at_ms bigint NOT NULL,
    changed_by    text NOT NULL,
    CONSTRAINT revisions_changed_by_shape CHECK (changed_by ~ '^[a-z0-9.]{1,40}$')
);

-- Envers writes the whole product as it was after each change: revtype 0 added, 1 changed, 2 removed.
CREATE TABLE products_aud (
    id          bigint NOT NULL,
    rev         bigint NOT NULL CONSTRAINT products_aud_revision_fk REFERENCES revisions,
    revtype     smallint NOT NULL,
    seller      text,
    name        text,
    price_paise bigint,
    CONSTRAINT products_aud_pk PRIMARY KEY (id, rev),
    CONSTRAINT products_aud_revtype CHECK (revtype IN (0, 1, 2))
);
CREATE INDEX products_aud_by_rev ON products_aud (rev);

-- History you can trust is history nobody can edit: rows are added, never changed or deleted, by any writer.
-- (TRUNCATE is a table owner's operation and is not covered; the application's database user should not own the tables.)
CREATE FUNCTION history_is_append_only() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'history_is_append_only: % on %', TG_OP, TG_TABLE_NAME USING ERRCODE = 'check_violation';
END $$ LANGUAGE plpgsql;
CREATE TRIGGER revisions_append_only BEFORE UPDATE OR DELETE ON revisions FOR EACH ROW EXECUTE FUNCTION history_is_append_only();
CREATE TRIGGER products_aud_append_only BEFORE UPDATE OR DELETE ON products_aud FOR EACH ROW EXECUTE FUNCTION history_is_append_only();
