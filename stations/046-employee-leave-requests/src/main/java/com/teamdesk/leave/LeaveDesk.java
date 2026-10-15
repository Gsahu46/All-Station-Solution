package com.teamdesk.leave;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.ErrorResponseException;

import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.temporal.ChronoUnit;

@Service
class LeaveDesk {

    /** Demo rule: a request spans at most 6 weeks (so at most 30 working days). Weekends are free; holidays are not modelled. */
    static final int MAX_SPAN_DAYS = 42;

    record RequestView(long id, long employeeId, LocalDate startDate, LocalDate endDate, int days, String reason, String status) {
        static RequestView of(LeaveRequest r) {
            return new RequestView(r.getId(), r.getEmployee().getId(), r.getStartDate(), r.getEndDate(), r.getDays(), r.getReason(), r.getStatus().name());
        }
    }

    record ApprovalView(long requestId, String status, int days, long employeeId, int balanceDays) {
    }

    record BalanceView(long employeeId, String name, int balanceDays) {
    }

    private final EmployeeRepository employees;
    private final LeaveRequestRepository requests;

    LeaveDesk(EmployeeRepository employees, LeaveRequestRepository requests) {
        this.employees = employees;
        this.requests = requests;
    }

    @Transactional
    RequestView request(long employeeId, LocalDate start, LocalDate end, String reason) {
        if (end.isBefore(start)) {
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "Invalid dates", "endDate is before startDate.");
        }
        if (ChronoUnit.DAYS.between(start, end) >= MAX_SPAN_DAYS) {
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "Invalid dates", "A request covers at most " + MAX_SPAN_DAYS + " calendar days.");
        }
        int days = workingDays(start, end);
        if (days == 0) {
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "No working days", "Every date from " + start + " to " + end + " is a weekend.");
        }
        Employee employee = employees.findById(employeeId)
                .orElseThrow(() -> problem(HttpStatus.UNPROCESSABLE_CONTENT, "Unknown employee", "No employee " + employeeId + "."));
        return RequestView.of(requests.save(new LeaveRequest(employee, start, end, days, reason)));
    }

    /**
     * One transaction: the request and the employee are loaded into one persistence context, changed in memory, and
     * written together when the method returns. There is no save() call, and none is needed.
     */
    @Transactional
    ApprovalView approve(long id) {
        LeaveRequest request = requests.findWithEmployeeById(id)
                .orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "Leave request not found", "No leave request " + id + "."));
        if (request.getStatus() != LeaveRequest.Status.PENDING) {
            throw problem(HttpStatus.CONFLICT, "Already decided", "Leave request " + id + " is already " + request.getStatus() + ".");
        }
        Employee employee = request.getEmployee();
        if (employee.getBalanceDays() < request.getDays()) {
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "Not enough leave",
                    employee.getName() + " has " + employee.getBalanceDays() + " days left; this request needs " + request.getDays() + ".");
        }
        request.approve();
        return new ApprovalView(id, request.getStatus().name(), request.getDays(), employee.getId(), employee.getBalanceDays());
    }

    @Transactional(readOnly = true)
    BalanceView balance(long employeeId) {
        return employees.findById(employeeId).map(e -> new BalanceView(e.getId(), e.getName(), e.getBalanceDays()))
                .orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "Employee not found", "No employee " + employeeId + "."));
    }

    static int workingDays(LocalDate start, LocalDate end) {
        return (int) start.datesUntil(end.plusDays(1))
                .filter(d -> d.getDayOfWeek() != DayOfWeek.SATURDAY && d.getDayOfWeek() != DayOfWeek.SUNDAY).count();
    }

    static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setTitle(title);
        return new ErrorResponseException(status, p, null);
    }
}
