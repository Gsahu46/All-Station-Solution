CREATE TABLE authors (
    id     BIGINT      PRIMARY KEY,
    handle VARCHAR(30) NOT NULL CONSTRAINT authors_handle_unique UNIQUE
                               CONSTRAINT authors_handle_shape CHECK (handle ~ '^[a-z0-9_]{3,30}$')
);

CREATE TABLE posts (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    author_id  BIGINT        NOT NULL CONSTRAINT posts_author_fk REFERENCES authors (id),
    body       VARCHAR(500)  NOT NULL CONSTRAINT posts_body_not_blank CHECK (btrim(body) <> ''),
    created_at TIMESTAMPTZ   NOT NULL DEFAULT now()
);
-- The feed's order, newest first: read backwards, (created_at, id) finds "the posts after this one" directly.
CREATE INDEX posts_feed ON posts (created_at, id);
