-- Demo rules: minimum-KYC wallets ₹10,000 a day, full-KYC wallets ₹1,00,000 a day.
INSERT INTO kyc_tiers (tier, daily_limit_paise) VALUES ('minimum', 1000000), ('full', 10000000);
INSERT INTO wallets (id, owner, tier, balance_paise) VALUES
    (1001, 'Ananya', 'minimum', 50000),
    (1002, 'Vikram', 'full', 0);
