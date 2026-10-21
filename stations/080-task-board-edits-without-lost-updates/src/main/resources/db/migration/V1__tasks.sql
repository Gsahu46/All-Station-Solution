CREATE TABLE tasks (
    id          bigint GENERATED ALWAYS AS IDENTITY CONSTRAINT tasks_pk PRIMARY KEY,
    board       text NOT NULL,
    title       text NOT NULL,
    description text NOT NULL,
    status      text NOT NULL,
    assignee    text,
    -- Counts every change. Every update must name the version it was based on; the ETag is this number.
    version     bigint NOT NULL DEFAULT 0,
    CONSTRAINT tasks_status CHECK (status IN ('open', 'doing', 'done')),
    CONSTRAINT tasks_title_length CHECK (char_length(title) BETWEEN 1 AND 120),
    CONSTRAINT tasks_version_nonnegative CHECK (version >= 0),
    -- Two cards with the same title on one board confuse everyone: a business rule, so a 409 when broken.
    CONSTRAINT tasks_board_title_unique UNIQUE (board, title)
);

-- The board's activity feed: one row per accepted change, written in the same transaction.
CREATE TABLE task_changes (
    id      bigint GENERATED ALWAYS AS IDENTITY CONSTRAINT task_changes_pk PRIMARY KEY,
    task_id bigint NOT NULL CONSTRAINT task_changes_task_fk REFERENCES tasks ON DELETE CASCADE,
    version bigint NOT NULL,
    title   text NOT NULL,
    status  text NOT NULL,
    CONSTRAINT task_changes_one_per_version UNIQUE (task_id, version)
);

-- Every writer, not only this app, must move the version on by exactly one: an UPDATE that forgets it (the old
-- last-write-wins code) is refused. A CHECK cannot compare old and new rows, so this rule is a trigger.
CREATE FUNCTION tasks_version_must_increase() RETURNS trigger AS $$
BEGIN
    IF NEW.version <> OLD.version + 1 THEN
        RAISE EXCEPTION 'tasks_version_must_increase: version % to % on task %', OLD.version, NEW.version, OLD.id
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER tasks_version_must_increase BEFORE UPDATE ON tasks FOR EACH ROW EXECUTE FUNCTION tasks_version_must_increase();
