package com.taskloom.signups;

import org.springframework.context.annotation.Import;

/** Every test in SignupContract, run on MySQL 8.4. */
@Import(Databases.MySql.class)
class MySqlSignupContractTest extends SignupContract {
}
