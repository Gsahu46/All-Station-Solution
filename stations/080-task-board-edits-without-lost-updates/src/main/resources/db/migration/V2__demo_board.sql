INSERT INTO tasks (id, board, title, description, status, assignee) OVERRIDING SYSTEM VALUE VALUES (1, 'launch', 'Write the press release', 'One page, two quotes.', 'open', 'asha');
INSERT INTO tasks (id, board, title, description, status, assignee) OVERRIDING SYSTEM VALUE VALUES (2, 'launch', 'Book the venue', 'Capacity 200.', 'doing', 'ravi');
ALTER TABLE tasks ALTER COLUMN id RESTART WITH 3;
