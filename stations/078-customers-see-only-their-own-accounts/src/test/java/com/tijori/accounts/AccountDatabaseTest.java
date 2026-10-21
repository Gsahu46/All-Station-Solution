package com.tijori.accounts;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.transaction.support.TransactionTemplate;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/** The rules hold for every writer, not only this app: plain SQL straight to PostgreSQL, no Java checks on the way. */
class AccountDatabaseTest extends ApiTest {

    @Autowired
    TransactionTemplate tx;

    void violates(String constraint, String sql) {
        assertThatThrownBy(() -> jdbc.sql(sql).update()).isInstanceOf(DataIntegrityViolationException.class).hasMessageContaining(constraint);
    }

    @Test
    void accountRulesHoldWithoutJava() {
        violates("accounts_balance_nonnegative", "UPDATE accounts SET balance_paise = -1 WHERE id = 1001");
        violates("accounts_kind", "INSERT INTO accounts (id, kind, name, balance_paise) VALUES (2001, 'crypto', 'X', 0)");
        violates("account_holders_access", "UPDATE account_holders SET access = 'admin' WHERE account_id = 1001");
        violates("account_holders_pk", "INSERT INTO account_holders (account_id, customer_id, access) SELECT 1001, id, 'full' FROM customers WHERE email = 'zoya@example.com'");
        violates("transactions_amount_nonzero", "INSERT INTO transactions (account_id, booked_on, description, amount_paise) VALUES (1001, '2026-10-10', 'Nothing', 0)");
        violates("transactions_description_length", "INSERT INTO transactions (account_id, booked_on, description, amount_paise) VALUES (1001, '2026-10-10', '', 100)");
        violates("customers_email_lower", "UPDATE customers SET email = 'Zoya@Example.com' WHERE email = 'zoya@example.com'");
    }

    /**
     * A statement line and its balance change are one transaction. A debit that would overdraw is refused by the
     * balance CHECK, and its line goes with it: no statement ever shows a payment the balance does not.
     */
    @Test
    void aDebitThatWouldOverdrawLeavesNeitherLineNorBalance() throws Exception {
        long before = jdbc.sql("SELECT count(*) FROM transactions WHERE account_id = 1002").query(Long.class).single();
        assertThatThrownBy(() -> tx.executeWithoutResult(s -> {
            jdbc.sql("INSERT INTO transactions (account_id, booked_on, description, amount_paise) VALUES (1002, '2026-10-15', 'Laptop', -99900000)").update();
            jdbc.sql("UPDATE accounts SET balance_paise = balance_paise - 99900000 WHERE id = 1002").update();
        })).isInstanceOf(DataIntegrityViolationException.class).hasMessageContaining("accounts_balance_nonnegative");
        assertThat(jdbc.sql("SELECT count(*) FROM transactions WHERE account_id = 1002").query(Long.class).single()).isEqualTo(before);
        account("dev", 1002).andExpect(jsonPath("$.balancePaise").value(1890050));
    }

    @Test
    void theNewestStatementClosesAtTheCurrentBalance() throws Exception {
        statement("zoya", 1001, "2026-10").andExpect(jsonPath("$.closingBalancePaise").value(9850000));
    }
}
