package com.dakroute.fleet;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
class ServicePlanController {

    record ServicePlan(long vehicleId, String registration, String model, Powertrain powertrain, Body body,
                       int odometerKm, List<ServicePlanner.PlanItem> tasks) {
    }

    private final Fleet fleet;

    ServicePlanController(Fleet fleet) {
        this.fleet = fleet;
    }

    @GetMapping("/fleet/vehicles/{id}/service-plan")
    ServicePlan plan(@PathVariable long id, @RequestParam(required = false) @Min(1) @Max(100_000) Integer withinKm) {
        Vehicle v = fleet.find(id).orElseThrow(() -> {
            ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, "No vehicle has this id.");
            p.setTitle("Vehicle not found");
            return new ErrorResponseException(HttpStatus.NOT_FOUND, p, null);
        });
        // Challenge 2: filter after planning, so the plan's order and arithmetic stay in one place.
        List<ServicePlanner.PlanItem> tasks = ServicePlanner.plan(v).stream()
                .filter(t -> withinKm == null || t.dueInKm() <= withinKm)
                .toList();
        return new ServicePlan(v.id(), v.registration(), v.model(), v.powertrain(), v.body(), v.odometerKm(), tasks);
    }
}
