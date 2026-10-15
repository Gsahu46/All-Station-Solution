package com.fitnest.members;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDate;
import java.util.Locale;

/**
 * Java checks the shape of a request and gives friendly messages. The database enforces the rules (one member per
 * phone, no overlapping memberships) for every writer; when it refuses, the constraint's name says which rule, and
 * that becomes a 409. Asking first ("is this phone taken?") would race with another request; the constraint cannot.
 */
@RestController
class MemberController {

    record NewMember(@NotBlank @Size(max = 80) String name, @NotBlank @Size(max = 20) String phone) {
    }

    record NewMembership(@NotBlank @Size(max = 20) String planCode, @NotNull LocalDate startsOn) {
    }

    private final MemberStore store;

    MemberController(MemberStore store) {
        this.store = store;
    }

    @PostMapping("/members")
    @ResponseStatus(HttpStatus.CREATED)
    MemberStore.Member join(@Valid @RequestBody NewMember request) {
        String phone = Phones.normalise(request.phone())
                .orElseThrow(() -> problem(HttpStatus.BAD_REQUEST, "Invalid phone", "phone must be a 10-digit Indian mobile number."));
        try {
            return store.addMember(request.name().strip(), phone);
        } catch (DataIntegrityViolationException e) {
            throw refusal(e);
        }
    }

    @PostMapping("/members/{id}/memberships")
    @ResponseStatus(HttpStatus.CREATED)
    MemberStore.Membership buy(@PathVariable long id, @Valid @RequestBody NewMembership request) {
        store.member(id).orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "Member not found", "No member " + id + "."));
        MemberStore.Plan plan = store.plan(request.planCode().strip().toUpperCase(Locale.ROOT))
                .orElseThrow(() -> problem(HttpStatus.UNPROCESSABLE_CONTENT, "Unknown plan", "Plans are MONTHLY, QUARTERLY and ANNUAL."));
        LocalDate endsOn = request.startsOn().plusMonths(plan.months()).minusDays(1);   // the last day the member can come
        try {
            return store.addMembership(id, plan, request.startsOn(), endsOn);
        } catch (DataIntegrityViolationException e) {
            throw refusal(e);
        }
    }

    /** Which named constraint refused the row decides the answer; anything else is a bug and stays a 500. */
    private static RuntimeException refusal(DataIntegrityViolationException e) {
        String message = String.valueOf(e.getMessage());
        if (message.contains("members_phone_unique")) {
            return problem(HttpStatus.CONFLICT, "Phone already registered", "Another member already has this phone number.");
        }
        if (message.contains("memberships_no_overlap")) {
            return problem(HttpStatus.CONFLICT, "Overlapping membership", "This member already has a membership covering some of these days.");
        }
        return e;
    }

    private static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setTitle(title);
        return new ErrorResponseException(status, p, null);
    }
}
