-- Challenge 2: a tax rate per line, in whole percent (demo range 0 to 40).
ALTER TABLE invoice_lines ADD COLUMN tax_percent INT NOT NULL DEFAULT 0;
ALTER TABLE invoice_lines ADD CONSTRAINT invoice_lines_tax_range CHECK (tax_percent BETWEEN 0 AND 40);
