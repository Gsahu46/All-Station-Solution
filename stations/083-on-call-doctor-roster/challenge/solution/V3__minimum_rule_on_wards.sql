-- The same rule seen from the wards table: a minimum may not be raised above the doctors on call right now.
CREATE FUNCTION wards_minimum_is_met() RETURNS trigger AS $$
BEGIN
    IF (SELECT count(*) FROM roster WHERE ward = NEW.id AND on_call) < NEW.min_on_call THEN
        RAISE EXCEPTION 'wards_minimum_is_met: % needs %, fewer are on call', NEW.id, NEW.min_on_call USING ERRCODE = 'check_violation';
    END IF;
    RETURN NULL;
END $$ LANGUAGE plpgsql;
CREATE CONSTRAINT TRIGGER wards_minimum_is_met AFTER UPDATE OF min_on_call ON wards
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION wards_minimum_is_met();
