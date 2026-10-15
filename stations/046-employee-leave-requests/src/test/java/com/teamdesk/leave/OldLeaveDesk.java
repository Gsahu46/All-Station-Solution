package com.teamdesk.leave;

/**
 * The approval as it shipped, kept to reproduce the bug. No @Transactional: each repository call runs in its own
 * short transaction, so the entities it returns are detached the moment it returns.
 */
class OldLeaveDesk {

    private final LeaveRequestRepository requests;

    OldLeaveDesk(LeaveRequestRepository requests) {
        this.requests = requests;
    }

    /** Returns the balance it showed the manager. */
    int approve(long id) {
        LeaveRequest request = requests.findWithEmployeeById(id).orElseThrow();
        request.approve();       // status APPROVED, and the employee's balance goes down: in memory
        requests.save(request);  // merge copies the request's columns; the employee is not cascaded, so its change is dropped
        return request.getEmployee().getBalanceDays();
    }
}
