package com.taskloom.signin;

import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
class MeController {

    private final Accounts accounts;

    MeController(Accounts accounts) {
        this.accounts = accounts;
    }

    record Me(String name, String email, String workspace, String signedInWith) {
    }

    /** The account linked to the checked Google identity: nothing in the request can choose another. */
    @GetMapping("/me")
    Me me(@AuthenticationPrincipal TaskloomUser user) {
        Accounts.Account a = user.account();
        return new Me(a.name(), a.email(), a.workspace(), "google");
    }

    /** The workspace comes from the signed-in account, never from the request. */
    @GetMapping("/workspace/members")
    List<String> members(@AuthenticationPrincipal TaskloomUser user) {
        return accounts.memberNames(user.account().workspace());
    }
}
