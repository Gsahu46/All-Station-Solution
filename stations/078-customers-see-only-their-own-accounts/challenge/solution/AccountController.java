package com.tijori.accounts;

import jakarta.validation.constraints.Pattern;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.math.BigDecimal;
import java.time.YearMonth;
import java.util.List;

@RestController
class AccountController {

    private final Accounts accounts;

    AccountController(Accounts accounts) {
        this.accounts = accounts;
    }

    @GetMapping("/accounts")
    List<Accounts.Account> mine(@AuthenticationPrincipal UserDetails me) {
        return accounts.mine(me.getUsername());
    }

    /** Same rules as the JSON statement, because it is the same call. Rupees from paise with BigDecimal, never double. */
    @GetMapping(value = "/accounts/{id}/statements.csv", produces = "text/csv;charset=UTF-8")
    ResponseEntity<String> csv(@AuthenticationPrincipal UserDetails me, @PathVariable long id,
                               @RequestParam @Pattern(regexp = "\\d{4}-(0[1-9]|1[0-2])") String month) {
        Accounts.Statement statement = accounts.statement(me.getUsername(), id, YearMonth.parse(month));
        StringBuilder csv = new StringBuilder("date,description,amount\n");
        for (Accounts.Line line : statement.lines()) {
            String d = line.description();
            String quoted = d.contains(",") || d.contains("\"") ? "\"" + d.replace("\"", "\"\"") + "\"" : d;
            csv.append(line.bookedOn()).append(',').append(quoted).append(',').append(BigDecimal.valueOf(line.amountPaise(), 2).toPlainString()).append('\n');
        }
        return ResponseEntity.ok().header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"tijori-" + id + "-" + month + ".csv\"").body(csv.toString());
    }

    /** The customer comes from the sign-in, the account from the URL; the query needs both to find a row. */
    @GetMapping("/accounts/{id}")
    Accounts.Account account(@AuthenticationPrincipal UserDetails me, @PathVariable long id) {
        return accounts.account(me.getUsername(), id);
    }

    @GetMapping("/accounts/{id}/statements")
    Accounts.Statement statement(@AuthenticationPrincipal UserDetails me, @PathVariable long id,
                                 @RequestParam @Pattern(regexp = "\\d{4}-(0[1-9]|1[0-2])") String month) {
        return accounts.statement(me.getUsername(), id, YearMonth.parse(month));
    }
}
