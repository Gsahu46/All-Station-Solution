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

/**
 * Every query names the signed-in customer: the account id from the URL is only half of the WHERE clause. An
 * account that is not theirs finds no row, exactly like one that does not exist, so both are 404.
 */
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

    Account account(String customer, long accountId) {
        return jdbc.sql("""
                        SELECT a.id, a.kind, a.name, a.balance_paise, h.access
                        FROM accounts a
                        JOIN account_holders h ON h.account_id = a.id
                        JOIN customers c ON c.id = h.customer_id AND c.email = ?
                        WHERE a.id = ?""")
                .params(customer, accountId).query(Account.class).optional().orElseThrow(Accounts::notFound);
    }

    /**
     * One month's lines with opening and closing balances. One REPEATABLE READ transaction, so a payment landing
     * between the queries cannot make the lines and the balances disagree.
     */
    @Transactional(readOnly = true, isolation = Isolation.REPEATABLE_READ)
    Statement statement(String customer, long accountId, YearMonth month) {
        Account account = account(customer, accountId);
        if (!account.access().equals("full")) {
            // A holder, so we may say the account exists; this sign-in may see the balance, not the lines.
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "This sign-in may see the balance only");
        }
        LocalDate from = month.atDay(1);
        LocalDate to = month.plusMonths(1).atDay(1);
        List<Line> lines = jdbc.sql("""
                        SELECT t.booked_on, t.description, t.amount_paise
                        FROM transactions t
                        JOIN account_holders h ON h.account_id = t.account_id AND h.access = 'full'
                        JOIN customers c ON c.id = h.customer_id AND c.email = ?
                        WHERE t.account_id = ? AND t.booked_on >= ? AND t.booked_on < ?
                        ORDER BY t.booked_on, t.id""")
                .params(customer, accountId, from, to).query(Line.class).list();
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
