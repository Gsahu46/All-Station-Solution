-- MySQL's default collation (utf8mb4_0900_ai_ci) ignores case AND accents: jose@x.com and josé@x.com would be "equal".
-- utf8mb4_bin compares exactly, like PostgreSQL; the index on lower(email) then adds case-insensitivity, and nothing else.
CREATE TABLE signups (
    id         BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
    email      VARCHAR(254) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
    name       VARCHAR(80)  NOT NULL,
    created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT signups_email_shape CHECK (email LIKE '_%@_%' AND email NOT LIKE '% %')
);

-- A functional index (MySQL 8.0.13+): the same rule as PostgreSQL's, under the same name.
CREATE UNIQUE INDEX signups_email_unique ON signups ((lower(email)));
