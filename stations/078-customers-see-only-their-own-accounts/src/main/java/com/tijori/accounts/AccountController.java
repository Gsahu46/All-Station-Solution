package com.tijori.accounts;

import jakarta.validation.constraints.Pattern;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.YearMonth;

@RestController
class AccountController {

    private final Accounts accounts;

    AccountController(Accounts accounts) {
        this.accounts = accounts;
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
