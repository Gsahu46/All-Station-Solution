package com.kartwala.prices;

import org.hibernate.envers.RevisionListener;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

/** "Who" for the history: the signed-in user, or the person support is acting for (X-Changed-By). */
public class ChangedByListener implements RevisionListener {

    @Override
    public void newRevision(Object revision) {
        Authentication who = SecurityContextHolder.getContext().getAuthentication();
        if (who == null || !who.isAuthenticated()) {
            throw new IllegalStateException("A price change needs a signed-in user");
        }
        // Support fixes prices while the seller is on the phone: record the seller, not the support agent.
        String actingFor = RequestContextHolder.getRequestAttributes() instanceof ServletRequestAttributes r ? r.getRequest().getHeader("X-Changed-By") : null;
        ((Revision) revision).changedBy(actingFor != null ? actingFor : who.getName());
    }
}
