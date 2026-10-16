package com.taskloom.signups;

import org.springframework.context.annotation.Import;

/** Every test in SignupDatabase, run on PostgreSQL 17. */
@Import(Databases.Postgres.class)
class PostgresSignupDatabaseTest extends SignupDatabase {
}
