package com.splitsaathi.groups;

import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController
class GroupController {

    record SettleUpView(long groupId, Map<String, Long> balancesPaise, List<SettleUp.Payment> payments) {
    }

    private final Groups groups;

    GroupController(Groups groups) {
        this.groups = groups;
    }

    @PostMapping("/groups/{id}/expenses")
    @ResponseStatus(HttpStatus.CREATED)
    Groups.Expense add(@PathVariable long id, @Valid @RequestBody ExpenseRequest r) {
        Groups.Group g = group(id);
        member(g, r.paidBy());
        Map<String, Long> owed = switch (r.splitType()) {
            case EQUAL -> {
                if (r.participants() == null || r.participants().isEmpty()) {
                    throw unprocessable("EQUAL needs a non-empty participants list.");
                }
                r.participants().forEach(p -> member(g, p));
                if (r.participants().stream().distinct().count() != r.participants().size()) {
                    throw unprocessable("Each participant can be listed once.");
                }
                yield Splitter.equal(r.amountPaise(), r.participants());
            }
            case EXACT -> {
                if (r.exactPaise() == null || r.exactPaise().isEmpty()) {
                    throw unprocessable("EXACT needs exactPaise for each person.");
                }
                r.exactPaise().forEach((p, v) -> {
                    member(g, p);
                    if (v == null || v < 0) {
                        throw unprocessable("Each exact amount must be zero or more.");
                    }
                });
                long sum = r.exactPaise().values().stream().mapToLong(Long::longValue).sum();
                if (sum != r.amountPaise()) {
                    throw unprocessable("The exact amounts add up to " + sum + " paise, not " + r.amountPaise() + ".");
                }
                yield new LinkedHashMap<>(r.exactPaise()); // keeps the order people were listed in
            }
            case SHARES -> {
                if (r.shares() == null || r.shares().isEmpty()) {
                    throw unprocessable("SHARES needs a share for each person.");
                }
                r.shares().forEach((p, s) -> {
                    member(g, p);
                    if (s == null || s < 1 || s > 1000) {
                        throw unprocessable("Each share must be from 1 to 1000.");
                    }
                });
                yield Splitter.shares(r.amountPaise(), r.shares());
            }
        };
        return groups.add(g, r.description(), r.paidBy(), r.amountPaise(), owed);
    }

    @GetMapping("/groups/{id}/settle-up")
    SettleUpView settleUp(@PathVariable long id) {
        Groups.Group g = group(id);
        Map<String, Long> balances = groups.balances(g);
        return new SettleUpView(id, balances, SettleUp.payments(balances));
    }

    private Groups.Group group(long id) {
        return groups.find(id).orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "Group not found", "No group has this id."));
    }

    private static void member(Groups.Group g, String name) {
        if (!g.members().contains(name)) {
            throw unprocessable("Everyone in an expense must be a member of the group.");
        }
    }

    private static ErrorResponseException unprocessable(String detail) {
        return problem(HttpStatus.UNPROCESSABLE_CONTENT, "Invalid split", detail);
    }

    private static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setTitle(title);
        return new ErrorResponseException(status, p, null);
    }
}
