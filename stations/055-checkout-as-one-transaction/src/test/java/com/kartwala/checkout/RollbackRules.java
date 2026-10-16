package com.kartwala.checkout;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.transaction.annotation.Transactional;

/** Test-only bean: the same write, under the rules that decide whether it survives. */
class RollbackRules {

    static class PaymentDeclined extends Exception {   // a checked exception
        PaymentDeclined() {
            super("declined");
        }
    }

    private final JdbcClient jdbc;

    RollbackRules(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    private void writeAnOrder() {
        jdbc.sql("INSERT INTO orders (customer_id, total_paise) VALUES (7, 100)").update();
    }

    @Transactional
    public void checkedException() throws PaymentDeclined {
        writeAnOrder();
        throw new PaymentDeclined();   // checked: Spring COMMITS by default
    }

    @Transactional(rollbackFor = PaymentDeclined.class)
    public void checkedExceptionWithRollbackFor() throws PaymentDeclined {
        writeAnOrder();
        throw new PaymentDeclined();
    }

    @Transactional
    public void uncheckedException() {
        writeAnOrder();
        throw new IllegalStateException("bug");   // unchecked: rolled back
    }

    @Transactional(readOnly = true)
    public void writeInReadOnly() {
        writeAnOrder();
    }
}
