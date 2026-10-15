-- Demo data: hotels, rooms and guests are fictional.
INSERT INTO rooms (id, hotel, name, capacity) VALUES
    (101, 'Ghoomo Candolim, Goa', 'Deluxe sea view', 2),
    (102, 'Ghoomo Candolim, Goa', 'Family suite', 4);

INSERT INTO room_blocks (room_id, check_in, check_out, guest_name) VALUES
    (101, DATE '2026-06-10', DATE '2026-06-12', 'Asha Verma'),
    (101, DATE '2026-06-15', DATE '2026-06-16', 'Ravi Iyer');
