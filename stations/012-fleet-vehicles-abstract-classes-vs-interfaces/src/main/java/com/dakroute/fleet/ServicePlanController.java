package com.dakroute.fleet;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
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
    ServicePlan plan(@PathVariable long id) {
        Vehicle v = fleet.find(id).orElseThrow(() -> {
            ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, "No vehicle has this id.");
            p.setTitle("Vehicle not found");
            return new ErrorResponseException(HttpStatus.NOT_FOUND, p, null);
        });
        return new ServicePlan(v.id(), v.registration(), v.model(), v.powertrain(), v.body(), v.odometerKm(),
                ServicePlanner.plan(v));
    }
}
