package com.taskloom.signin;

import org.springframework.stereotype.Component;

import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Taskloom's own accounts, and which Google account (by its stable subject id, "sub") each is linked to.
 * Simulated: held in memory. shortcut: lost on restart, one pod only; a real app keeps both maps in its database.
 */
@Component
class Accounts {

    record Account(String id, String name, String email, String workspace) {
    }

    static final String NOT_INVITED = "not_invited";

    /** Google sub -> account. asha linked her Google account last week. */
    private final Map<String, Account> linked = new ConcurrentHashMap<>(Map.of(
            "100000000000000000001", new Account("acc-1", "Asha Rao", "asha@acme.example", "Acme")));

    /** Invited by a workspace admin, not yet signed in: lower-case email -> account waiting to be linked. */
    private final Map<String, Account> invited = new ConcurrentHashMap<>(Map.of(
            "meera@acme.example", new Account("acc-2", "Meera Iyer", "meera@acme.example", "Acme"),
            "kabir@globex.example", new Account("acc-3", "Kabir Shah", "kabir@globex.example", "Globex")));

    /** What the workspace admin's invite screen calls (the screen is not part of this station). */
    void invite(String email, String name, String workspace) {
        String key = email.toLowerCase(Locale.ROOT);
        invited.put(key, new Account("acc-" + UUID.randomUUID(), name, key, workspace));
    }

    /**
     * The account for this Google sign-in: by sub if already linked, else by an invited email that Google says is
     * verified. An unverified email never links: anyone can put any address on an account and not verify it.
     */
    Optional<Account> forGoogle(String sub, String email, Boolean emailVerified) {
        Account account = linked.get(sub);
        if (account != null || email == null || !Boolean.TRUE.equals(emailVerified)) {
            return Optional.ofNullable(account);
        }
        Account invite = invited.remove(email.toLowerCase(Locale.ROOT));
        if (invite != null) {
            linked.put(sub, invite);
        }
        return Optional.ofNullable(invite);
    }
}
