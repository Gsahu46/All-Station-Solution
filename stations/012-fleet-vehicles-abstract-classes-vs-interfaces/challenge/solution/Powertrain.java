package com.dakroute.fleet;

import java.util.List;

/** What moves the vehicle. Each value brings its own tasks. Intervals are demo rules, not a manufacturer's schedule. */
public enum Powertrain implements ServiceItems {
    DIESEL(List.of(new ServiceTask("Engine oil change", 15_000), new ServiceTask("Fuel filter", 30_000),
            new ServiceTask("Diesel particulate filter clean", 60_000))),
    PETROL(List.of(new ServiceTask("Engine oil change", 10_000), new ServiceTask("Spark plugs", 20_000))),
    ELECTRIC(List.of(new ServiceTask("Battery health check", 20_000), new ServiceTask("Battery coolant", 40_000))),
    // Challenge 1: one new value, with its own tasks. No other class changes.
    CNG(List.of(new ServiceTask("Engine oil change", 10_000), new ServiceTask("Gas leak check", 10_000),
            new ServiceTask("Cylinder hydro-test", 100_000)));

    private final List<ServiceTask> tasks;

    Powertrain(List<ServiceTask> tasks) {
        this.tasks = tasks;
    }

    @Override
    public List<ServiceTask> tasks() {
        return tasks;
    }
}
