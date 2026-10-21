-- Demo workspace: ravi owns four documents. The Brand folder (with a Logos folder inside) is shared with team design,
-- which includes asha and the whole team brand-leads (neha). meera edits the roadmap. kabir has nothing yet.
INSERT INTO documents (id, title, body) VALUES
    ('d-guidelines', 'Brand guidelines', 'Use the teal from the palette; never stretch the logo.'),
    ('d-logo-brief', 'Logo refresh brief', 'Three directions by Friday.'),
    ('d-roadmap', 'Q4 roadmap', 'Ship sharing, then search.'),
    ('d-salaries', 'Salary bands 2027', 'Confidential.');

INSERT INTO relation_tuples (object_type, object_id, relation, subject_type, subject_id, subject_relation) VALUES
    ('team', 'design', 'member', 'user', 'asha', ''),
    ('team', 'design', 'member', 'team', 'brand-leads', 'member'),
    ('team', 'brand-leads', 'member', 'user', 'neha', ''),
    ('folder', 'f-logos', 'parent', 'folder', 'f-brand', ''),
    ('folder', 'f-brand', 'viewer', 'team', 'design', 'member'),
    ('doc', 'd-guidelines', 'parent', 'folder', 'f-brand', ''),
    ('doc', 'd-logo-brief', 'parent', 'folder', 'f-logos', ''),
    ('doc', 'd-guidelines', 'owner', 'user', 'ravi', ''),
    ('doc', 'd-logo-brief', 'owner', 'user', 'ravi', ''),
    ('doc', 'd-roadmap', 'owner', 'user', 'ravi', ''),
    ('doc', 'd-salaries', 'owner', 'user', 'ravi', ''),
    ('doc', 'd-roadmap', 'editor', 'user', 'meera', '');
