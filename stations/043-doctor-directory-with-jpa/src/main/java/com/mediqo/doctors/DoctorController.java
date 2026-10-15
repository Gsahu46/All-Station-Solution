package com.mediqo.doctors;

import jakarta.validation.constraints.Pattern;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
class DoctorController {

    private final DoctorDirectory directory;

    DoctorController(DoctorDirectory directory) {
        this.directory = directory;
    }

    /** Both filters optional, any letter case: /doctors?speciality=cardiology&city=Pune */
    @GetMapping("/doctors")
    List<DoctorView> search(@RequestParam(required = false) @Pattern(regexp = "[\\p{L} ]{2,40}", message = "letters and spaces, 2 to 40") String speciality,
                            @RequestParam(required = false) @Pattern(regexp = "[\\p{L} ]{2,40}", message = "letters and spaces, 2 to 40") String city) {
        return directory.search(speciality == null ? null : speciality.strip(), city == null ? null : city.strip());
    }

    @GetMapping("/doctors/{id}")
    DoctorView one(@PathVariable long id) {
        return directory.one(id).orElseThrow(() -> {
            ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, "No doctor " + id + ".");
            p.setTitle("Doctor not found");
            return new ErrorResponseException(HttpStatus.NOT_FOUND, p, null);
        });
    }
}
