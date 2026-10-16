-- Challenge 2: the same index, now carrying status in its leaf entries, so counts never visit the table.
-- Same name, so nothing that refers to it changes. The cost: wider entries, written on every insert.
DROP INDEX shipments_phone_booked_on;
CREATE INDEX shipments_phone_booked_on ON shipments (phone, booked_on) INCLUDE (status);
