-- The catalogue the search reads, and the table the old search leaked: prescriptions hold patients' names and phones.
CREATE TABLE medicines (
    id                    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name                  VARCHAR(100) NOT NULL,
    strength              VARCHAR(30)  NOT NULL,
    form                  VARCHAR(20)  NOT NULL,
    price_paise           BIGINT       NOT NULL,
    prescription_required BOOLEAN      NOT NULL,
    CONSTRAINT medicines_price_positive CHECK (price_paise > 0),
    CONSTRAINT medicines_form_known     CHECK (form IN ('TABLET', 'CAPSULE', 'SYRUP', 'CREAM', 'INJECTION', 'DROPS'))
);

-- One row per product: "Paracetamol" and "PARACETAMOL" 500 mg tablets are the same product.
CREATE UNIQUE INDEX medicines_unique_product ON medicines (lower(name), strength, form);

CREATE TABLE prescriptions (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    patient_name  VARCHAR(100) NOT NULL,
    patient_phone VARCHAR(15)  NOT NULL,
    medicine_id   BIGINT       NOT NULL,
    doctor        VARCHAR(100) NOT NULL,
    issued_on     DATE         NOT NULL,
    CONSTRAINT prescriptions_medicine_fk FOREIGN KEY (medicine_id) REFERENCES medicines (id)
);
