-- Challenge 2: an earn can be reversed once; the reversal names the same order.
ALTER TABLE point_entries DROP CONSTRAINT point_entries_reason_known;
ALTER TABLE point_entries ADD CONSTRAINT point_entries_reason_known CHECK (reason IN ('EARN', 'REDEEM', 'REVERSE'));
ALTER TABLE point_entries DROP CONSTRAINT point_entries_sign_matches;
ALTER TABLE point_entries ADD CONSTRAINT point_entries_sign_matches CHECK (
    (reason = 'EARN' AND order_ref IS NOT NULL AND delta >= 0)
    OR (reason = 'REDEEM' AND order_ref IS NULL AND delta < 0)
    OR (reason = 'REVERSE' AND order_ref IS NOT NULL AND delta <= 0));
ALTER TABLE point_entries DROP CONSTRAINT point_entries_order_once;
ALTER TABLE point_entries ADD CONSTRAINT point_entries_order_once UNIQUE (customer_id, order_ref, reason);
