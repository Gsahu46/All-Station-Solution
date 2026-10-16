-- Equality column first, range column second: one phone's shipments sit together, in date order.
-- Built after the data is loaded; on a live table use CREATE INDEX CONCURRENTLY (see Production).
CREATE INDEX shipments_phone_booked_on ON shipments (phone, booked_on);
ANALYZE shipments;
