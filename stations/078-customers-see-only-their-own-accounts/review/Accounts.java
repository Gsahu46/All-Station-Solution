package com.tijori.accounts;

import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.time.LocalDate;
import java.time.YearMonth;
import java.util.List;

/** Accounts and statements for signed-in customers. */
@Service
class Accounts {

    record Account(long id, String kind, String name, long balancePaise, String access) {
    }

    record Line(LocalDate bookedOn, String description, long amountPaise) {
    }

    record Statement(long accountId, String month, long openingBalancePaise, long closingBalancePaise, List<Line> lines) {
    }

    private final JdbcClient jdbc;

    Accounts(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    /** Find the account, then check the holder: one simple query each, and a clear 403 when it is someone else's. */
    Account account(String customer, long accountId) {
        Account account = jdbc.sql("SELECT id, kind, name, balance_paise, 'full' AS access FROM accounts WHERE id = ?")
                .param(accountId).query(Account.class).optional().orElseThrow(Accounts::notFound);
        boolean holder = jdbc.sql("SELECT EXISTS (SELECT 1 FROM account_holders h JOIN customers c ON c.id = h.customer_id WHERE h.account_id = ? AND c.email = ?)")
                .params(accountId, customer).query(Boolean.class).single();
        if (!holder) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "This account belongs to another customer");
        }
        return account;
    }

    /**
     * One month's lines with opening and closing balances. One REPEATABLE READ transaction, so a payment landing
     * between the queries cannot make the lines and the balances disagree.
     */
    @Transactional(readOnly = true, isolation = Isolation.REPEATABLE_READ)
    Statement statement(String customer, long accountId, YearMonth month) {
        Account account = account(customer, accountId);
        LocalDate from = month.atDay(1);
        LocalDate to = month.plusMonths(1).atDay(1);
        List<Line> lines = jdbc.sql("""
                        SELECT booked_on, description, amount_paise FROM transactions
                        WHERE account_id = ? AND booked_on >= ? AND booked_on < ?
                        ORDER BY booked_on, id""")   // the holder was checked above
                .params(accountId, from, to).query(Line.class).list();
        long after = jdbc.sql("SELECT coalesce(sum(amount_paise), 0) FROM transactions WHERE account_id = ? AND booked_on >= ?")
                .params(accountId, to).query(Long.class).single();
        long closing = account.balancePaise() - after;
        long opening = closing - lines.stream().mapToLong(Line::amountPaise).sum();
        return new Statement(accountId, month.toString(), opening, closing, lines);
    }

    static ResponseStatusException notFound() {
        return new ResponseStatusException(HttpStatus.NOT_FOUND, "No such account");
    }
}
