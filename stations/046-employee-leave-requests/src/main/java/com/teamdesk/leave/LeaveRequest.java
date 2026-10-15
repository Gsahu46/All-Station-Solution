package com.teamdesk.leave;

import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import jakarta.persistence.Version;

import java.time.LocalDate;

@Entity
@Table(name = "leave_requests")
public class LeaveRequest {

    public enum Status { PENDING, APPROVED, REJECTED }

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "employee_id")
    private Employee employee;
    private LocalDate startDate;
    private LocalDate endDate;
    private int days;
    private String reason;
    @Enumerated(EnumType.STRING)
    private Status status = Status.PENDING;
    @Version
    private long version;

    protected LeaveRequest() {
    }

    LeaveRequest(Employee employee, LocalDate startDate, LocalDate endDate, int days, String reason) {
        this.employee = employee;
        this.startDate = startDate;
        this.endDate = endDate;
        this.days = days;
        this.reason = reason;
    }

    /** Changes two objects: this request and the employee's balance. Only a managed pair is saved by itself. */
    void approve() {
        status = Status.APPROVED;
        employee.deduct(days);
    }

    public Long getId() {
        return id;
    }

    public Employee getEmployee() {
        return employee;
    }

    public LocalDate getStartDate() {
        return startDate;
    }

    public LocalDate getEndDate() {
        return endDate;
    }

    public int getDays() {
        return days;
    }

    public String getReason() {
        return reason;
    }

    public Status getStatus() {
        return status;
    }
}
