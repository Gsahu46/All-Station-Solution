package com.teamdesk.leave;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;

@Entity
@Table(name = "employees")
public class Employee {

    @Id
    private Long id;
    private String name;
    private int balanceDays;
    @Version   // two approvals for the same person at once: the later commit fails instead of overwriting the balance
    private long version;

    protected Employee() {
    }

    public Long getId() {
        return id;
    }

    public String getName() {
        return name;
    }

    public int getBalanceDays() {
        return balanceDays;
    }

    void deduct(int days) {
        balanceDays -= days;
    }

    void refund(int days) {
        balanceDays += days;
    }
}
