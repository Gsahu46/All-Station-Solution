CREATE TABLE clinics (
    id      BIGINT       PRIMARY KEY,
    name    VARCHAR(80)  NOT NULL,
    city    VARCHAR(40)  NOT NULL,
    address VARCHAR(200) NOT NULL
);

CREATE TABLE doctors (
    id                  BIGINT       PRIMARY KEY,
    name                VARCHAR(80)  NOT NULL,
    speciality          VARCHAR(40)  NOT NULL,
    city                VARCHAR(40)  NOT NULL,
    registration_number VARCHAR(20)  NOT NULL,   -- public: printed on prescriptions
    personal_phone      VARCHAR(15)  NOT NULL,   -- private: for the clinic only
    salary_paise        BIGINT       NOT NULL,   -- private
    internal_notes      VARCHAR(500),            -- private
    clinic_id           BIGINT       NOT NULL,
    CONSTRAINT doctors_registration_unique UNIQUE (registration_number),
    CONSTRAINT doctors_clinic_fk           FOREIGN KEY (clinic_id) REFERENCES clinics (id),
    CONSTRAINT doctors_salary_positive     CHECK (salary_paise > 0)
);
-- upper(), because Spring Data writes IgnoreCase as upper(column) = upper(?): an index on lower() would never be used.
CREATE INDEX doctors_speciality_city ON doctors (upper(speciality), upper(city));
