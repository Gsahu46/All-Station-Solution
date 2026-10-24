package com.taskloom.support;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.time.Clock;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Tokens each team may spend on summaries per day (India time). Checked before a call, charged with the real usage
 * after it. A limit, not an exact figure: requests already under way when the limit is reached still finish, so a team
 * can pass it by those requests' tokens.
 * shortcut: in memory, one server; across servers or restarts it belongs in a shared store.
 */
@Component
class TeamBudget {

    private static final ZoneId INDIA = ZoneId.of("Asia/Kolkata");
    private final int tokensPerDay;
    private final Clock clock;
    private final Map<String, Integer> used = new ConcurrentHashMap<>();

    TeamBudget(@Value("${taskloom.budget.tokens-per-team-per-day}") int tokensPerDay, Clock clock) {
        this.tokensPerDay = tokensPerDay;
        this.clock = clock;
    }

    boolean hasRoom(String team) {
        return used.getOrDefault(key(team), 0) < tokensPerDay;
    }

    void charge(String team, int tokens) {
        used.merge(key(team), tokens, Integer::sum);
    }

    int used(String team) {
        return used.getOrDefault(key(team), 0);
    }

    private String key(String team) {
        return team + "/" + LocalDate.now(clock.withZone(INDIA));
    }
}
