package com.taskloom.webinars;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.ZoneOffset;

@RestController
class WebinarController {

    /**
     * startsAt is the host's wall-clock time, with no offset; zone says where that wall is. The offset is only for
     * the one hour a year when the host's clock shows the same time twice.
     */
    record NewWebinar(@NotBlank @Size(max = 120) String title, @NotNull LocalDateTime startsAt, @NotBlank String zone,
                      @NotNull @Min(15) @Max(480) Integer durationMinutes, Schedule.Repeat repeat,
                      @Min(1) @Max(12) Integer sessions, ZoneOffset offset) {
    }

    private final Schedule schedule;

    WebinarController(Schedule schedule) {
        this.schedule = schedule;
    }

    @PostMapping("/webinars")
    ResponseEntity<Schedule.WebinarView> create(@Valid @RequestBody NewWebinar body) {
        Schedule.WebinarView webinar = schedule.create(body.title().strip(), body.startsAt(), region(body.zone(), "zone"), body.offset(),
                body.durationMinutes(), body.repeat() == null ? Schedule.Repeat.NONE : body.repeat(), body.sessions() == null ? 1 : body.sessions());
        return ResponseEntity.created(URI.create("/webinars/" + webinar.id())).body(webinar);
    }

    @GetMapping("/webinars/{id}")
    Schedule.WebinarView get(@PathVariable long id, @RequestParam(required = false) String viewerZone) {
        return schedule.find(id, viewerZone == null ? null : region(viewerZone, "viewerZone"))
                .orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "Webinar not found", "No webinar " + id + "."));
    }

    /**
     * Only region ids such as Asia/Kolkata (and UTC). A fixed offset like +05:30 knows nothing about daylight saving,
     * and abbreviations like IST are ambiguous (India, Ireland, Israel).
     */
    static ZoneId region(String id, String field) {
        if (!ZoneId.getAvailableZoneIds().contains(id)) {
            throw problem(HttpStatus.BAD_REQUEST, "Unknown time zone", field + " must be a time zone region such as Asia/Kolkata or Europe/London, not \"" + id + "\".");
        }
        return ZoneId.of(id);
    }

    static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setTitle(title);
        return new ErrorResponseException(status, p, null);
    }
}
