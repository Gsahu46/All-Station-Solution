CREATE TABLE doctors (
    id         BIGINT       PRIMARY KEY,
    name       VARCHAR(80)  NOT NULL,
    speciality VARCHAR(40)  NOT NULL,
    active     BOOLEAN      NOT NULL DEFAULT true
);

CREATE TABLE appointments (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    doctor_id    BIGINT      NOT NULL,
    patient_name VARCHAR(80) NOT NULL,
    starts_at    TIMESTAMPTZ NOT NULL,
    status       VARCHAR(10) NOT NULL,
    fee_paise    BIGINT      NOT NULL,
    CONSTRAINT appointments_doctor_fk    FOREIGN KEY (doctor_id) REFERENCES doctors (id),
    CONSTRAINT appointments_status_known CHECK (status IN ('BOOKED', 'COMPLETED', 'CANCELLED', 'NO_SHOW')),
    CONSTRAINT appointments_fee_not_negative CHECK (fee_paise >= 0)
);
CREATE INDEX appointments_doctor_time ON appointments (doctor_id, starts_at);

-- An appointment can lead to several follow-ups (a test next week, a review next month): one-to-many.
CREATE TABLE follow_ups (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    appointment_id BIGINT NOT NULL,
    due_on         DATE   NOT NULL,
    reason         VARCHAR(80) NOT NULL,
    CONSTRAINT follow_ups_appointment_fk FOREIGN KEY (appointment_id) REFERENCES appointments (id)
);
