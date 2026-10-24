package com.taskloom.support;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/** Builds the prompt, checks the budget, calls the model, and keeps the last summary of each ticket. */
@Component
class Summaries {

    record Summary(String ticketId, String summary, boolean cached, int inputTokens, int outputTokens,
                   int omittedMessages, Map<String, Integer> removed) {
    }

    /** The team's daily budget is spent. */
    static final class OverBudget extends RuntimeException {
    }

    private static final Logger log = LoggerFactory.getLogger(Summaries.class);
    private static final int MAX_SUMMARY_CHARS = 2_000;
    private final ModelClient model;
    private final TeamBudget budget;
    private final int maxInputChars;
    // The last summary of each ticket, by the hash of the prompt it was made from: an unchanged thread costs nothing.
    private final Map<String, Map.Entry<String, Summary>> last = new ConcurrentHashMap<>();

    Summaries(ModelClient model, TeamBudget budget, @Value("${taskloom.model.max-input-chars}") int maxInputChars) {
        this.model = model;
        this.budget = budget;
        this.maxInputChars = maxInputChars;
    }

    Summary summarise(Tickets.Ticket ticket) {
        Prompt prompt = Prompt.of(ticket, maxInputChars);
        String hash = sha256(prompt.system() + "\n" + prompt.user());
        Map.Entry<String, Summary> previous = last.get(ticket.id());
        if (previous != null && previous.getKey().equals(hash)) {
            Summary s = previous.getValue();
            return new Summary(s.ticketId(), s.summary(), true, 0, 0, s.omittedMessages(), s.removed());
        }
        // max_tokens already caps what one summary can cost.
        ModelClient.Answer answer = model.summarise(prompt);
        budget.charge(ticket.team(), answer.inputTokens() + answer.outputTokens());
        // The model's words are untrusted too: cut to size, and personal data removed again in case it was made up.
        String text = Redactor.redact(answer.text().strip(), ticket.customerName()).text();
        text = text.length() > MAX_SUMMARY_CHARS ? text.substring(0, MAX_SUMMARY_CHARS) : text;
        log.info("Summary of {} for team {}: {} input and {} output tokens, stop reason {}", ticket.id(), ticket.team(),
                answer.inputTokens(), answer.outputTokens(), answer.stopReason());   // never the prompt or the summary
        Summary s = new Summary(ticket.id(), text, false, answer.inputTokens(), answer.outputTokens(), prompt.omittedMessages(), prompt.removed());
        last.put(ticket.id(), Map.entry(hash, s));
        return s;
    }

    /** For tests: start without remembered summaries. */
    void forgetAll() {
        last.clear();
    }

    private static String sha256(String s) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(s.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }
}
