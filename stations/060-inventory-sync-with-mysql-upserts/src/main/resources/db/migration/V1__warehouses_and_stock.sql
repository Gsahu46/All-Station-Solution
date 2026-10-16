CREATE TABLE warehouses (
    id   BIGINT       NOT NULL PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE stock_levels (
    id           BIGINT      NOT NULL AUTO_INCREMENT PRIMARY KEY,
    warehouse_id BIGINT      NOT NULL,
    sku          VARCHAR(30) NOT NULL,
    quantity     INT         NOT NULL,
    updated_at   TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    -- The rule the old sync only checked in Java: one row per SKU per warehouse. ON DUPLICATE KEY UPDATE needs it.
    CONSTRAINT stock_levels_warehouse_sku UNIQUE (warehouse_id, sku),
    CONSTRAINT stock_levels_warehouse_fk FOREIGN KEY (warehouse_id) REFERENCES warehouses (id),
    CONSTRAINT stock_levels_quantity_range CHECK (quantity BETWEEN 0 AND 1000000),
    CONSTRAINT stock_levels_sku_shape CHECK (REGEXP_LIKE(sku, '^[A-Z0-9-]{3,30}$', 'c'))
);
