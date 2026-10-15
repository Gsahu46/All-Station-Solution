-- Optional email, unique whatever the letter case. NULLs are never equal, so many members may have none.
ALTER TABLE members ADD COLUMN email VARCHAR(120);
CREATE UNIQUE INDEX members_email_unique ON members (lower(email));
