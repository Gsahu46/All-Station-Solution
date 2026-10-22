package com.kartwala.prices;

import org.hibernate.envers.RevisionListener;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;

/**
 * "Who" comes from the signed-in user, never from the request body. A change with nobody signed in is refused:
 * an anonymous line in a price history is worth nothing.
 */
public class ChangedByListener implements RevisionListener {

    @Override
    public void newRevision(Object revision) {
        Authentication who = SecurityContextHolder.getContext().getAuthentication();
        if (who == null || !who.isAuthenticated()) {
            throw new IllegalStateException("A price change needs a signed-in user");
        }
        ((Revision) revision).changedBy(who.getName());
    }
}
