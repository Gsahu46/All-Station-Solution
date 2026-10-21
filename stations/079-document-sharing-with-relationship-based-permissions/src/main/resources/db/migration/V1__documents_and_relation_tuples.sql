CREATE TABLE documents (
    id         text CONSTRAINT documents_pk PRIMARY KEY,
    title      text NOT NULL,
    body       text NOT NULL,
    CONSTRAINT documents_id_shape CHECK (id ~ '^[a-z0-9-]{1,40}$'),
    CONSTRAINT documents_title_length CHECK (char_length(title) BETWEEN 1 AND 120)
);

-- Every permission is one tuple: object, relation, subject. "team:design#member is viewer of folder:brand" is one row;
-- who is in team:design is other rows. Access is worked out from the tuples on every request, never copied.
CREATE TABLE relation_tuples (
    object_type      text NOT NULL,
    object_id        text NOT NULL,
    relation         text NOT NULL,
    subject_type     text NOT NULL,
    subject_id       text NOT NULL,
    subject_relation text NOT NULL DEFAULT '',
    CONSTRAINT relation_tuples_pk PRIMARY KEY (object_type, object_id, relation, subject_type, subject_id, subject_relation),
    CONSTRAINT relation_tuples_id_shape CHECK (object_id ~ '^[a-z0-9.-]{1,40}$' AND subject_id ~ '^[a-z0-9.-]{1,40}$'),
    -- Which relations each type of object has.
    CONSTRAINT relation_tuples_relation_for_type CHECK (
           (object_type = 'team' AND relation = 'member')
        OR (object_type = 'folder' AND relation IN ('viewer', 'editor', 'parent'))
        OR (object_type = 'doc' AND relation IN ('owner', 'editor', 'viewer', 'parent'))),
    -- A parent is a folder; anyone else is a user, or every member of a team.
    CONSTRAINT relation_tuples_subject CHECK (
           (relation = 'parent' AND subject_type = 'folder' AND subject_relation = '')
        OR (relation <> 'parent' AND subject_type = 'user' AND subject_relation = '')
        OR (relation <> 'parent' AND subject_type = 'team' AND subject_relation = 'member'))
);
-- A document or folder sits in at most one folder, and has at most one owner.
CREATE UNIQUE INDEX relation_tuples_one_parent ON relation_tuples (object_type, object_id) WHERE relation = 'parent';
CREATE UNIQUE INDEX relation_tuples_one_owner ON relation_tuples (object_type, object_id) WHERE relation = 'owner';
-- "Which objects is this subject related to?": the walk from a user to their teams and their grants.
CREATE INDEX relation_tuples_by_subject ON relation_tuples (subject_type, subject_id, relation);

-- Simulated notification ("ravi shared Brand guidelines with you"), written in the same transaction as the share.
CREATE TABLE share_notices (
    id        bigint GENERATED ALWAYS AS IDENTITY CONSTRAINT share_notices_pk PRIMARY KEY,
    doc_id    text NOT NULL CONSTRAINT share_notices_doc_fk REFERENCES documents ON DELETE CASCADE,
    shared_to text NOT NULL,
    relation  text NOT NULL,
    shared_by text NOT NULL,
    CONSTRAINT share_notices_relation CHECK (relation IN ('viewer', 'editor'))
);
