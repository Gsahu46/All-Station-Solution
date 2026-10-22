package com.mediqo.roster;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
class RosterController {

    record Request(@NotNull @Pattern(regexp = "dr\\.[a-z]{2,30}") String doctor) {
    }

    record Handover(@NotNull @Pattern(regexp = "dr\\.[a-z]{2,30}") String from, @NotNull @Pattern(regexp = "dr\\.[a-z]{2,30}") String to) {
    }

    record MinimumRequest(@Min(1) @Max(50) int minOnCall) {
    }

    private final Roster roster;

    RosterController(Roster roster) {
        this.roster = roster;
    }

    /** Safe to repeat: a doctor who is already off gets the same answer and nothing changes. */
    @PostMapping("/rosters/{ward}/off-call")
    Roster.OffCall offCall(@PathVariable String ward, @Valid @RequestBody Request body) {
        return roster.offCall(ward, body.doctor());
    }

    /** Safe to repeat: once the handover is done, the same request gets the same answer. */
    @PostMapping("/rosters/{ward}/handover")
    Roster.OffCall handover(@PathVariable String ward, @Valid @RequestBody Handover body) {
        if (body.from().equals(body.to())) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "A doctor cannot hand over to themselves");
        }
        return roster.handover(ward, body.from(), body.to());
    }

    @PutMapping("/rosters/{ward}/minimum")
    Roster.Minimum minimum(@PathVariable String ward, @Valid @RequestBody MinimumRequest body) {
        return roster.minimum(ward, body.minOnCall());
    }
}
