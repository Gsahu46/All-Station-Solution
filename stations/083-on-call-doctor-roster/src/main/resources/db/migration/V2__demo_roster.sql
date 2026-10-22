-- Demo night roster: Cardiology needs one doctor on call and has two; Orthopaedics needs one and has three.
INSERT INTO wards (id, name, min_on_call) VALUES ('cardiology', 'Cardiology', 1), ('orthopaedics', 'Orthopaedics', 1);
INSERT INTO roster (ward, doctor, on_call) VALUES
    ('cardiology', 'dr.sharma', true), ('cardiology', 'dr.iyer', true), ('cardiology', 'dr.menon', false),
    ('orthopaedics', 'dr.bose', true), ('orthopaedics', 'dr.khan', true), ('orthopaedics', 'dr.rao', true);
