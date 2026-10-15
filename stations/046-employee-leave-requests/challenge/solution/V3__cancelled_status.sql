-- Challenge 2: approved leave can be cancelled.
ALTER TABLE leave_requests DROP CONSTRAINT leave_requests_status_known;
ALTER TABLE leave_requests ADD CONSTRAINT leave_requests_status_known CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED'));
