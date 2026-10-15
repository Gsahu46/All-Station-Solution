-- Version 1, as it shipped: primary keys only. Every rule lived in Java, so any other writer (an import script, the
-- front desk's spreadsheet sync) could store two members with one phone, or a membership that ends before it starts.
-- Released migrations are never edited: the fixes are V2.
CREATE TABLE members (
    id    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name  VARCHAR(80) NOT NULL,
    phone VARCHAR(20) NOT NULL
);

CREATE TABLE memberships (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    member_id   BIGINT      NOT NULL,
    plan        VARCHAR(40) NOT NULL,   -- "Monthly", "monthly ", "MONTHLY": a name typed per row
    starts_on   DATE        NOT NULL,
    ends_on     DATE        NOT NULL,
    price_paise BIGINT      NOT NULL
);
