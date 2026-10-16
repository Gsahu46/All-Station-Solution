package com.taskloom.signups;

import org.springframework.context.annotation.Import;

/** Every test in SignupContract, run on PostgreSQL 17. */
@Import(Databases.Postgres.class)
class PostgresSignupContractTest extends SignupContract {
}
