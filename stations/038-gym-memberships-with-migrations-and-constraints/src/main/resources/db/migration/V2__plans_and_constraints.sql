-- Version 2: the rules move into the database, named, so every writer meets them.
-- Runs in one transaction (PostgreSQL DDL is transactional): if existing rows break a new rule, nothing changes and
-- the migration fails, naming the constraint. Fix the rows (see the runbook query in the station), then run it again.

-- Plans get their own table (3NF): a plan's name, length and list price depend on the plan, not on each membership.
CREATE TABLE plans (
    code        VARCHAR(20)  PRIMARY KEY,
    name        VARCHAR(40)  NOT NULL,
    months      SMALLINT     NOT NULL,
    price_paise BIGINT       NOT NULL,
    CONSTRAINT plans_months_range   CHECK (months BETWEEN 1 AND 24),
    CONSTRAINT plans_price_positive CHECK (price_paise > 0)
);
INSERT INTO plans (code, name, months, price_paise) VALUES
    ('MONTHLY', 'Monthly', 1, 149900),
    ('QUARTERLY', 'Quarterly', 3, 399900),
    ('ANNUAL', 'Annual', 12, 1199900);

-- Phones are stored in one form, 10 digits, so "98765 43210" and "+91 9876543210" are the same number to UNIQUE.
UPDATE members SET phone = right(regexp_replace(phone, '[^0-9]', '', 'g'), 10);
ALTER TABLE members
    ADD CONSTRAINT members_phone_digits CHECK (phone ~ '^[6-9][0-9]{9}$'),
    ADD CONSTRAINT members_phone_unique UNIQUE (phone);

-- Memberships point at a plan by code. The price stays on the membership: it is what this member paid that day,
-- a fact about the sale, not a copy of the plan's current price.
ALTER TABLE memberships ADD COLUMN plan_code VARCHAR(20);
UPDATE memberships SET plan_code = upper(trim(plan));
ALTER TABLE memberships ALTER COLUMN plan_code SET NOT NULL, DROP COLUMN plan;

CREATE EXTENSION IF NOT EXISTS btree_gist;   -- lets one EXCLUDE constraint mix "=" on a number with "&&" on dates
ALTER TABLE memberships
    ADD CONSTRAINT memberships_member_fk   FOREIGN KEY (member_id) REFERENCES members (id),
    ADD CONSTRAINT memberships_plan_fk     FOREIGN KEY (plan_code) REFERENCES plans (code),
    ADD CONSTRAINT memberships_dates_order CHECK (ends_on >= starts_on),
    ADD CONSTRAINT memberships_price_positive CHECK (price_paise > 0);
-- A statement of its own, after the dates check: in one ALTER, building this index runs daterange() on a row that ends
-- before it starts and fails with "range lower bound must be less than or equal to range upper bound", which names no
-- rule. Separately, such a row is refused by memberships_dates_order first, by name.
-- One member, no two memberships covering the same day.
ALTER TABLE memberships
    ADD CONSTRAINT memberships_no_overlap EXCLUDE USING gist (member_id WITH =, daterange(starts_on, ends_on, '[]') WITH &&);
