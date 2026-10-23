-- One row per shipment. The seller's own reference identifies it, so a batch sent twice cannot create it twice.
CREATE TABLE shipments (
    id            bigint GENERATED ALWAYS AS IDENTITY CONSTRAINT shipments_pk PRIMARY KEY,
    ref           text NOT NULL,
    from_pincode  text NOT NULL,
    to_name       text NOT NULL,
    to_line1      text NOT NULL,
    to_city       text NOT NULL,
    to_pincode    text NOT NULL,
    to_phone      text NOT NULL,
    weight_grams  integer NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT shipments_ref_unique UNIQUE (ref),
    CONSTRAINT shipments_ref_shape CHECK (ref ~ '^[A-Z0-9-]{3,40}$'),
    CONSTRAINT shipments_pincodes CHECK (from_pincode ~ '^[1-9][0-9]{5}$' AND to_pincode ~ '^[1-9][0-9]{5}$'),
    CONSTRAINT shipments_phone CHECK (to_phone ~ '^[6-9][0-9]{9}$'),
    CONSTRAINT shipments_weight CHECK (weight_grams BETWEEN 1 AND 50000),
    CONSTRAINT shipments_address_present CHECK (length(trim(to_name)) > 0 AND length(trim(to_line1)) > 0 AND length(trim(to_city)) > 0)
);
