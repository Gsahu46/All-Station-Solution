package com.taskloom.signin;

import org.springframework.security.core.authority.AuthorityUtils;
import org.springframework.security.oauth2.core.oidc.user.DefaultOidcUser;
import org.springframework.security.oauth2.core.oidc.user.OidcUser;

/** The signed-in person: the checked Google identity, and the Taskloom account it is linked to. */
class TaskloomUser extends DefaultOidcUser {

    private final Accounts.Account account;

    TaskloomUser(OidcUser google, Accounts.Account account) {
        super(Accounts.ADMINS.contains(account.id()) ? AuthorityUtils.createAuthorityList("ROLE_MEMBER", "ROLE_ADMIN") : AuthorityUtils.createAuthorityList("ROLE_MEMBER"), google.getIdToken(), google.getUserInfo(), "sub");
        this.account = account;
    }

    Accounts.Account account() {
        return account;
    }
}
