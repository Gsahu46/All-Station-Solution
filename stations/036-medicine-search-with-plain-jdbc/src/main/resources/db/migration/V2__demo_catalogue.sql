-- Demo data: products and prices are illustrative, patients are fictional, phone numbers are not real.
INSERT INTO medicines (name, strength, form, price_paise, prescription_required) VALUES
    ('Paracetamol', '500 mg', 'TABLET', 2_000, false),
    ('Paracetamol', '650 mg', 'TABLET', 3_050, false),
    ('Paracetamol', '125 mg/5 ml', 'SYRUP', 4_500, false),
    ('Amoxicillin', '500 mg', 'CAPSULE', 9_800, true),
    ('Azithromycin', '500 mg', 'TABLET', 12_000, true),
    ('Cetirizine', '10 mg', 'TABLET', 1_800, false),
    ('Metformin', '500 mg', 'TABLET', 3_500, true),
    ('Amlodipine', '5 mg', 'TABLET', 4_200, true),
    ('Pantoprazole', '40 mg', 'TABLET', 9_500, true),
    ('Ibuprofen', '400 mg', 'TABLET', 2_400, false),
    ('Clotrimazole', '1%', 'CREAM', 8_900, false),
    ('Moxifloxacin', '0.5%', 'DROPS', 18_500, true),
    ('Insulin glargine', '100 IU/ml', 'INJECTION', 74_000, true),
    ('St. John''s Wort', '300 mg', 'CAPSULE', 45_000, false),
    ('Oral rehydration salts', '21 g', 'SYRUP', 2_100, false);

INSERT INTO prescriptions (patient_name, patient_phone, medicine_id, doctor, issued_on) VALUES
    ('Asha Verma', '90000 00001', (SELECT id FROM medicines WHERE name = 'Metformin'), 'Dr Mehta', DATE '2026-09-02'),
    ('Ravi Iyer', '90000 00002', (SELECT id FROM medicines WHERE name = 'Amlodipine'), 'Dr Rao', DATE '2026-09-11'),
    ('Fatima Shaikh', '90000 00003', (SELECT id FROM medicines WHERE name = 'Azithromycin'), 'Dr Mehta', DATE '2026-10-01');
