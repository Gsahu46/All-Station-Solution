-- Demo data: clinics, doctors, phone numbers and notes are fictional.
INSERT INTO clinics (id, name, city, address) VALUES
    (1, 'Mediqo Koregaon Park', 'Pune', 'Lane 5, Koregaon Park, Pune 411001'),
    (2, 'Mediqo Indiranagar', 'Bengaluru', '100 Feet Road, Indiranagar, Bengaluru 560038');

INSERT INTO doctors (id, name, speciality, city, registration_number, personal_phone, salary_paise, internal_notes, clinic_id) VALUES
    (1, 'Dr Asha Mehta', 'Cardiology', 'Pune', 'MMC-2011-04512', '90000 10001', 45000000, 'On notice period until December', 1),
    (2, 'Dr Ravi Iyer', 'Dermatology', 'Pune', 'MMC-2015-11873', '90000 10002', 30000000, NULL, 1),
    (3, 'Dr Meena Rao', 'Paediatrics', 'Bengaluru', 'KMC-2009-07731', '90000 10003', 38000000, 'Asked for weekends off', 2),
    (4, 'Dr Kabir Khan', 'Cardiology', 'Bengaluru', 'KMC-2018-02290', '90000 10004', 32000000, NULL, 2),
    (5, 'Dr Fatima Ali', 'Cardiology', 'Pune', 'MMC-2020-09045', '90000 10005', 28000000, NULL, 1),
    (6, 'Dr John Dsouza', 'Orthopaedics', 'Bengaluru', 'KMC-2012-05518', '90000 10006', 36000000, NULL, 2);
