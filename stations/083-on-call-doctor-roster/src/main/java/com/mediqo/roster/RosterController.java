package com.mediqo.roster;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
class RosterController {

    record Request(@NotNull @Pattern(regexp = "dr\\.[a-z]{2,30}") String doctor) {
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
}
