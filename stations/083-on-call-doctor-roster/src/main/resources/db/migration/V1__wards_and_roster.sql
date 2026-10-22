CREATE TABLE wards (
    id          text CONSTRAINT wards_pk PRIMARY KEY,
    name        text NOT NULL,
    min_on_call integer NOT NULL,
    CONSTRAINT wards_min_on_call_positive CHECK (min_on_call >= 1)
);

CREATE TABLE roster (
    ward    text NOT NULL CONSTRAINT roster_ward_fk REFERENCES wards,
    doctor  text NOT NULL,
    on_call boolean NOT NULL,
    CONSTRAINT roster_pk PRIMARY KEY (ward, doctor),
    CONSTRAINT roster_doctor_shape CHECK (doctor ~ '^dr\.[a-z]{2,30}$')
);

-- One row per real change: who went off or on call, and when.
CREATE TABLE roster_changes (
    id        bigint GENERATED ALWAYS AS IDENTITY CONSTRAINT roster_changes_pk PRIMARY KEY,
    ward      text NOT NULL,
    doctor    text NOT NULL,
    went      text NOT NULL,
    changed_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT roster_changes_went CHECK (went IN ('off', 'on'))
);

-- The rule for every writer: a ward never has fewer doctors on call than its minimum. It spans rows, so it is a
-- constraint trigger, checked at commit. Its limit: two READ COMMITTED transactions committing at the same instant
-- can each see the other's change as not yet committed. The application therefore also runs SERIALIZABLE.
-- It watches changes of on_call; deleting a roster row is not covered (this API never deletes one).
CREATE FUNCTION wards_keep_min_on_call() RETURNS trigger AS $$
DECLARE
    on_call_now integer;
    minimum integer;
BEGIN
    SELECT count(*) FILTER (WHERE r.on_call), w.min_on_call INTO on_call_now, minimum
    FROM wards w LEFT JOIN roster r ON r.ward = w.id WHERE w.id = NEW.ward GROUP BY w.min_on_call;
    IF on_call_now < minimum THEN
        RAISE EXCEPTION 'wards_keep_min_on_call: % has % on call, needs %', NEW.ward, on_call_now, minimum USING ERRCODE = 'check_violation';
    END IF;
    RETURN NULL;
END $$ LANGUAGE plpgsql;
CREATE CONSTRAINT TRIGGER wards_keep_min_on_call AFTER UPDATE OF on_call ON roster
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION wards_keep_min_on_call();
