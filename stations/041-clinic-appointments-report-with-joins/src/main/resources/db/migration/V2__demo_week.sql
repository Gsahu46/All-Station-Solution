-- Demo data: the week of 5 to 11 October 2026 (India time). Doctors and patients are fictional.
INSERT INTO doctors (id, name, speciality, active) VALUES
    (1, 'Dr Mehta', 'Cardiology', true),
    (2, 'Dr Iyer', 'Dermatology', true),
    (3, 'Dr Rao', 'Paediatrics', true),
    (4, 'Dr Khan', 'Orthopaedics', true),     -- joined this week: no appointments yet
    (5, 'Dr Das', 'Cardiology', false);       -- retired: not in the report

INSERT INTO appointments (doctor_id, patient_name, starts_at, status, fee_paise) VALUES
    (1, 'Asha Verma',  TIMESTAMPTZ '2026-10-05 10:00 Asia/Kolkata', 'COMPLETED', 80000),   -- id 1: two follow-ups
    (1, 'Ravi Iyer',   TIMESTAMPTZ '2026-10-06 11:00 Asia/Kolkata', 'COMPLETED', 80000),   -- id 2: one follow-up
    (1, 'Meena Rao',   TIMESTAMPTZ '2026-10-07 12:00 Asia/Kolkata', 'NO_SHOW', 80000),
    (1, 'Kabir Shah',  TIMESTAMPTZ '2026-10-08 09:30 Asia/Kolkata', 'CANCELLED', 80000),
    (2, 'Fatima Ali',  TIMESTAMPTZ '2026-10-05 15:00 Asia/Kolkata', 'COMPLETED', 60000),
    (2, 'John Dsouza', TIMESTAMPTZ '2026-10-11 23:30 Asia/Kolkata', 'BOOKED', 60000),      -- Sunday night: still this week in India
    (3, 'Baby Anaya',  TIMESTAMPTZ '2026-10-09 10:00 Asia/Kolkata', 'COMPLETED', 50000),
    (3, 'Baby Ivaan',  TIMESTAMPTZ '2026-10-12 00:15 Asia/Kolkata', 'BOOKED', 50000),      -- Monday: next week
    (5, 'Old Patient', TIMESTAMPTZ '2026-10-06 10:00 Asia/Kolkata', 'COMPLETED', 70000);

INSERT INTO follow_ups (appointment_id, due_on, reason) VALUES
    (1, DATE '2026-10-12', 'ECG review'),
    (1, DATE '2026-11-05', 'Blood test'),
    (2, DATE '2026-10-20', 'BP check');
