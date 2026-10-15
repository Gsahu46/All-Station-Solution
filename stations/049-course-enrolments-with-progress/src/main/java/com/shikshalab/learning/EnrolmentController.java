package com.shikshalab.learning;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;
import java.util.List;

@RestController
class EnrolmentController {

    /** Demo: the student is named in the body. A real platform takes it from the login. */
    record NewEnrolment(@NotNull Long studentId) {
    }

    record Progress(@NotNull @Min(0) Integer lessonsCompleted) {
    }

    private final EnrolmentDesk desk;

    EnrolmentController(EnrolmentDesk desk) {
        this.desk = desk;
    }

    @PostMapping("/courses/{id}/enrolments")
    ResponseEntity<EnrolmentDesk.EnrolmentView> enrol(@PathVariable long id, @Valid @RequestBody NewEnrolment body) {
        EnrolmentDesk.EnrolmentView enrolment = desk.enrol(id, body.studentId());
        return ResponseEntity.created(URI.create("/enrolments/" + enrolment.id())).body(enrolment);
    }

    @PatchMapping("/enrolments/{id}/progress")
    EnrolmentDesk.EnrolmentView progress(@PathVariable long id, @Valid @RequestBody Progress body) {
        return desk.recordProgress(id, body.lessonsCompleted());
    }

    @GetMapping("/students/{id}/courses")
    List<EnrolmentDesk.EnrolmentView> courses(@PathVariable long id) {
        return desk.coursesOf(id);
    }
}
