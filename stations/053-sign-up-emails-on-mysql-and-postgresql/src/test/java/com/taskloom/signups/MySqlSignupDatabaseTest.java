package com.taskloom.signups;

import org.springframework.context.annotation.Import;

/** Every test in SignupDatabase, run on MySQL 8.4. */
@Import(Databases.MySql.class)
class MySqlSignupDatabaseTest extends SignupDatabase {
}
