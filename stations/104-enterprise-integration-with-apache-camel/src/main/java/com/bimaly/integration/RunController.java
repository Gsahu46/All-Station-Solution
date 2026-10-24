package com.bimaly.integration;

import org.springframework.http.HttpStatus;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

/** What happened to a file: for the operations team and for the bank's support line. */
@RestController
class RunController {

    private final Runs runs;

    RunController(Runs runs) {
        this.runs = runs;
    }

    @GetMapping("/integration/runs/{id}")
    Runs.Run run(@PathVariable long id) {
        return runs.find(id).orElseThrow(() -> new ErrorResponseException(HttpStatus.NOT_FOUND));
    }
}
