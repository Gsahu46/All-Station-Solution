package com.mediqo.wards;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.authority.AuthorityUtils;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;
import java.time.LocalTime;
import java.util.List;
import java.util.UUID;

@RestController
class WardController {

    record NewPrescription(@NotBlank @Size(max = 80) String drug, @Min(1) @Max(5000) int doseMg,
                           @Min(1) @Max(6) int timesPerDay, @Min(1) @Max(90) int days) {
    }

    /** What reception sees: who, when, with whom. The reason is clinical, so only clinicians see it. */
    record Slot(LocalTime time, String patient, String doctor, String reason) {
    }

    private final Ward ward;

    WardController(Ward ward) {
        this.ward = ward;
    }

    @GetMapping("/appointments/today")
    @PreAuthorize("hasAuthority('appointments:read')")
    List<Slot> today(Authentication staff) {
        boolean clinician = AuthorityUtils.authorityListToSet(staff.getAuthorities()).contains("notes:read");
        return ward.today.stream().map(a -> new Slot(a.time(), a.patientName(), a.doctor(), clinician ? a.reason() : null)).toList();
    }

    @GetMapping("/patients/{patientId}/notes")
    @PreAuthorize("hasAuthority('notes:read') and (@ward.inCareOf(authentication, #patientId) or @ward.breakGlass(authentication))")
    List<Ward.Note> notes(@PathVariable String patientId) {
        Authentication staff = SecurityContextHolder.getContext().getAuthentication();
        boolean emergency = !ward.inCareOf(staff, patientId);
        ward.notesReads.add(new Ward.NotesRead(staff.getName(), patientId, emergency, emergency ? Ward.emergencyReason().strip() : null));
        return ward.notes.getOrDefault(patientId, List.of());
    }

    @GetMapping("/audit/notes-reads")
    @PreAuthorize("hasAuthority('audit:read')")
    List<Ward.NotesRead> notesReads() {
        return ward.notesReads;
    }

    @PostMapping("/patients/{patientId}/prescriptions")
    @PreAuthorize("hasAuthority('prescriptions:write') and @ward.inCareOf(authentication, #patientId)")
    ResponseEntity<Ward.Prescription> prescribe(@PathVariable String patientId, @Valid @RequestBody NewPrescription body, Authentication doctor) {
        Ward.Prescription rx = new Ward.Prescription("RX-" + UUID.randomUUID().toString().substring(0, 8), patientId,
                body.drug().strip(), body.doseMg(), body.timesPerDay(), body.days(), doctor.getName());
        ward.prescriptions.add(rx);
        return ResponseEntity.created(URI.create("/patients/" + patientId + "/prescriptions/" + rx.id())).body(rx);
    }
}
