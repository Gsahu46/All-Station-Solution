package com.seatsure.holds;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.net.URI;
import java.util.List;
import java.util.UUID;

@RestController
class HoldController {

    /** Either named seats or a count of any seats, never both. Demo rule: at most 6 seats per hold. */
    record NewHold(@NotBlank @Size(max = 60) String customer,
                   @Size(min = 1, max = 6) List<@Pattern(regexp = "[A-Z][0-9]{1,2}") String> seats,
                   @Min(1) @Max(6) Integer count) {
    }

    private final Holds holds;

    HoldController(Holds holds) {
        this.holds = holds;
    }

    @PostMapping("/shows/{id}/holds")
    ResponseEntity<Holds.Hold> hold(@PathVariable long id, @Valid @RequestBody NewHold body) {
        if ((body.seats() == null) == (body.count() == null)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Send either seats or count");
        }
        Holds.Hold hold = body.seats() != null ? holds.hold(id, body.customer().strip(), body.seats().stream().distinct().toList())
                : holds.holdAny(id, body.customer().strip(), body.count());
        return ResponseEntity.created(URI.create("/holds/" + hold.id())).body(hold);
    }

    @PostMapping("/holds/{id}/confirm")
    Holds.Hold confirm(@PathVariable UUID id) {
        return holds.confirm(id);
    }

    /** 503 with Retry-After: the seat is not taken, just busy for a moment. */
    @ExceptionHandler(Holds.SeatBusy.class)
    ResponseEntity<ProblemDetail> busy() {
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE).header("Retry-After", "1")
                .body(ProblemDetail.forStatusAndDetail(HttpStatus.SERVICE_UNAVAILABLE, "Someone is booking this seat right now. Try again in a moment."));
    }
}
