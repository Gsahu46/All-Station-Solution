package com.ghoomo.holds;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;
import java.time.LocalDate;

@RestController
class HoldController {

    record HoldRequest(@Positive long roomTypeId, @NotNull LocalDate date, @NotBlank @Email @Size(max = 200) String guestEmail) {
    }

    private final Holds holds;

    HoldController(Holds holds) {
        this.holds = holds;
    }

    /** 201 for a new hold; 200 with the same hold when the same request is sent again with the same key. */
    @PostMapping("/holds")
    ResponseEntity<Holds.Hold> create(@RequestHeader("Idempotency-Key") @Pattern(regexp = "[A-Za-z0-9-]{8,64}") String key,
                                      @Valid @RequestBody HoldRequest body) {
        Holds.Created created;
        try {
            created = holds.create(key, body.roomTypeId(), body.date(), body.guestEmail());
        } catch (DuplicateKeyException sameKeyAtTheSameMoment) {
            // Another request with this key committed first; ours was rolled back, room included. Answer with theirs.
            created = holds.replay(key, Holds.sha256(body.roomTypeId() + "|" + body.date() + "|" + body.guestEmail().strip().toLowerCase(java.util.Locale.ROOT)))
                    .orElseThrow(() -> sameKeyAtTheSameMoment);
        }
        Holds.Hold hold = created.hold();
        return created.replay() ? ResponseEntity.ok(hold) : ResponseEntity.created(URI.create("/holds/" + hold.id())).body(hold);
    }

    /** No guest details in the answer: hold ids are short numbers (demo), and anyone can try one. */
    @GetMapping("/holds/{id}")
    Holds.Hold hold(@PathVariable long id) {
        return holds.find(id).orElseThrow(() -> Holds.problem(HttpStatus.NOT_FOUND, "No such hold."));
    }
}
