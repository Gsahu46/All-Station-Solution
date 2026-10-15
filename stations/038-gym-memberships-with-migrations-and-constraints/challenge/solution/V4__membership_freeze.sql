-- Frozen days per membership, never more than 30. The overlap rule (memberships_no_overlap) also guards the new end.
ALTER TABLE memberships ADD COLUMN frozen_days SMALLINT NOT NULL DEFAULT 0;
ALTER TABLE memberships ADD CONSTRAINT memberships_freeze_limit CHECK (frozen_days BETWEEN 0 AND 30);
