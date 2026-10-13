package com.dakroute.fleet;

import java.util.Comparator;
import java.util.List;

/** Turns a vehicle's tasks into a plan: when each is next due, soonest first. Plain Java, tested without Spring. */
final class ServicePlanner {

    /** One line of the plan. dueSoon: within 10% of the task's interval (a demo rule). */
    record PlanItem(String task, int everyKm, int nextDueKm, int dueInKm, boolean dueSoon) {
    }

    private ServicePlanner() {
    }

    static List<PlanItem> plan(Vehicle v) {
        return v.parts().stream()
                .flatMap(part -> part.tasks().stream())
                .map(t -> item(t, v.odometerKm()))
                .sorted(Comparator.comparingInt(PlanItem::dueInKm).thenComparing(PlanItem::task))
                .toList();
    }

    /** Due at every multiple of the interval: at 128,400 km a 15,000 km task is next due at 135,000. At exactly 30,000 it is due now. */
    static PlanItem item(ServiceTask t, int odometerKm) {
        int nextDue = Math.max(t.everyKm(), Math.ceilDiv(odometerKm, t.everyKm()) * t.everyKm());
        int dueIn = nextDue - odometerKm;
        return new PlanItem(t.name(), t.everyKm(), nextDue, dueIn, dueIn <= t.everyKm() / 10);
    }
}
