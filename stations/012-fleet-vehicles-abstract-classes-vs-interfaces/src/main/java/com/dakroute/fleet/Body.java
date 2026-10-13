package com.dakroute.fleet;

import java.util.List;

/** What the vehicle is shaped like and carries. Independent of the powertrain: an EV van is ELECTRIC + VAN. */
public enum Body implements ServiceItems {
    TRUCK(List.of(new ServiceTask("Brake check", 10_000), new ServiceTask("Tyre rotation", 15_000),
            new ServiceTask("Axle greasing", 5_000))),
    VAN(List.of(new ServiceTask("Brake check", 15_000), new ServiceTask("Tyre rotation", 10_000))),
    TWO_WHEELER(List.of(new ServiceTask("Chain lubrication", 1_000), new ServiceTask("Brake check", 5_000)));

    private final List<ServiceTask> tasks;

    Body(List<ServiceTask> tasks) {
        this.tasks = tasks;
    }

    @Override
    public List<ServiceTask> tasks() {
        return tasks;
    }
}
