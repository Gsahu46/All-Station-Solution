ALTER TABLE device_sessions DROP CONSTRAINT device_sessions_revoked_reason;
ALTER TABLE device_sessions ADD CONSTRAINT device_sessions_revoked_reason CHECK (revoked_reason IN ('logout', 'removed', 'reuse', 'limit'));
