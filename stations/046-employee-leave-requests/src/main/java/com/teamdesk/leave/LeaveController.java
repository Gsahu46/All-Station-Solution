package com.teamdesk.leave;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import org.springframework.dao.OptimisticLockingFailureException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDate;

@RestController
class LeaveController {

    record NewRequest(@NotNull Long employeeId, @NotNull LocalDate startDate, @NotNull LocalDate endDate,
                      @NotBlank @Size(max = 200) String reason) {
    }

    private final LeaveDesk desk;

    LeaveController(LeaveDesk desk) {
        this.desk = desk;
    }

    @PostMapping("/leave-requests")
    @ResponseStatus(HttpStatus.CREATED)
    LeaveDesk.RequestView request(@Valid @RequestBody NewRequest body) {
        return desk.request(body.employeeId(), body.startDate(), body.endDate(), body.reason().strip());
    }

    /** Demo: no login, so anyone may approve. A real desk checks that the caller is the employee's manager. */
    @PostMapping("/leave-requests/{id}/approval")
    LeaveDesk.ApprovalView approve(@PathVariable long id) {
        return desk.approve(id);
    }

    @GetMapping("/employees/{id}/leave-balance")
    LeaveDesk.BalanceView balance(@PathVariable long id) {
        return desk.balance(id);
    }

    /** A @Version check failed at commit: another approval changed the request or the balance first. */
    @ExceptionHandler(OptimisticLockingFailureException.class)
    ProblemDetail changedMeanwhile() {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT,
                "Another approval changed this request or this balance at the same moment. Reload and try again.");
        p.setTitle("Changed meanwhile");
        return p;
    }
}
