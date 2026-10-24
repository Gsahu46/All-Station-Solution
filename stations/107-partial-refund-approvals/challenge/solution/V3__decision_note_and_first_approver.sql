-- Challenge 1: why a refund was rejected. Challenge 2: two approvers above a second limit.
ALTER TABLE refunds ADD COLUMN decision_note VARCHAR(200);
ALTER TABLE refunds ADD COLUMN needs_two_approvers BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE refunds ADD COLUMN first_approved_by TEXT;
-- Two different people, neither of them the asker.
ALTER TABLE refunds ADD CONSTRAINT refunds_two_different_approvers
    CHECK (first_approved_by IS NULL OR (first_approved_by <> requested_by AND (decided_by IS NULL OR decided_by <> first_approved_by)));
