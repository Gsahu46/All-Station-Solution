package com.dakroute.fleet;

import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.Set;
import java.util.stream.Collectors;

import static org.assertj.core.api.Assertions.assertThat;

/** The planner on its own: due-date arithmetic, and that composition never leaks tasks between parts. */
class ServicePlannerTest {

    private final ServiceTask oil = new ServiceTask("Engine oil change", 15_000);

    @Test
    void nextDueIsTheNextMultipleOfTheInterval() {
        assertThat(ServicePlanner.item(oil, 0).nextDueKm()).isEqualTo(15_000);
        assertThat(ServicePlanner.item(oil, 14_999).nextDueKm()).isEqualTo(15_000);
        assertThat(ServicePlanner.item(oil, 30_000).dueInKm()).isZero();        // exactly at the mark: due now
        assertThat(ServicePlanner.item(oil, 30_000).dueSoon()).isTrue();
        assertThat(ServicePlanner.item(oil, 30_001).nextDueKm()).isEqualTo(45_000);
    }

    @Test
    void everyCombinationOfPartsGetsExactlyTheTasksOfItsTwoParts() {
        for (Powertrain p : Powertrain.values()) {
            for (Body b : Body.values()) {
                Set<String> expected = new HashSet<>();
                p.tasks().forEach(t -> expected.add(t.name()));
                b.tasks().forEach(t -> expected.add(t.name()));
                Vehicle v = new Vehicle(0, "TEST", "test", p, b, 1_000);
                assertThat(ServicePlanner.plan(v).stream().map(ServicePlanner.PlanItem::task).collect(Collectors.toSet()))
                        .as(p + " + " + b).isEqualTo(expected);
            }
        }
    }
}
