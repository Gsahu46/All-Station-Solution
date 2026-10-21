package com.mediqo.wards;

import org.springframework.security.core.Authentication;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.time.LocalTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * Simulated hospital records, held in memory: patients, who cares for them, their clinical notes, today's
 * appointments and the prescriptions written. shortcut: lost on restart; a real system keeps these in its database.
 */
@Component("ward")
class Ward {

    record Patient(String id, String name, String ward, String doctor) {
    }

    record Note(String writtenBy, String text) {
    }

    record Appointment(LocalTime time, String patientId, String patientName, String doctor, String reason) {
    }

    record Prescription(String id, String patientId, String drug, int doseMg, int timesPerDay, int days, String prescribedBy) {
    }

    /** Which ward each nurse works on (demo rule). */
    static final Map<String, String> NURSE_WARD = Map.of("nurse.ritu", "Cardiology", "nurse.joseph", "Orthopaedics");

    final Map<String, Patient> patients = Map.of(
            "P-1001", new Patient("P-1001", "Kavya Menon", "Cardiology", "dr.sharma"),
            "P-1002", new Patient("P-1002", "Imran Ali", "Cardiology", "dr.sharma"),
            "P-2001", new Patient("P-2001", "Lakshmi Pillai", "Orthopaedics", "dr.bose"));

    final Map<String, List<Note>> notes = Map.of(
            "P-1001", List.of(new Note("dr.sharma", "Chest pain on exertion; ECG shows ST changes. Start beta blocker.")),
            "P-1002", List.of(new Note("dr.sharma", "Post-angioplasty review: stable.")),
            "P-2001", List.of(new Note("dr.bose", "Left knee replacement, day 2. Mobilising with frame.")));

    final List<Appointment> today = List.of(
            new Appointment(LocalTime.of(9, 30), "P-1001", "Kavya Menon", "dr.sharma", "Cardiology follow-up"),
            new Appointment(LocalTime.of(11, 0), "P-2001", "Lakshmi Pillai", "dr.bose", "Wound check"));

    final List<Prescription> prescriptions = new CopyOnWriteArrayList<>();

    record NotesRead(String staff, String patientId, boolean emergency, String reason) {
    }

    /** Who read whose notes. shortcut: in memory; a real audit log is append-only storage outside the app's reach. */
    final List<NotesRead> notesReads = new CopyOnWriteArrayList<>();

    /** The X-Emergency-Reason header of the current request, if any. */
    static String emergencyReason() {
        return RequestContextHolder.getRequestAttributes() instanceof ServletRequestAttributes r ? r.getRequest().getHeader("X-Emergency-Reason") : null;
    }

    /** Break-glass: only doctors, only with a reason someone can later judge. */
    public boolean breakGlass(Authentication staff) {
        String reason = emergencyReason();
        return reason != null && reason.strip().length() >= 10 && reason.length() <= 200
                && staff.getAuthorities().stream().anyMatch(a -> a.getAuthority().equals("ROLE_DOCTOR"));
    }

    Optional<Patient> patient(String id) {
        return Optional.ofNullable(patients.get(id));
    }

    /**
     * Least privilege, per patient: a doctor for their own patients, a nurse for patients on their ward. Used in
     * {@code @PreAuthorize}; an unknown patient is "not in your care" too, so ids cannot be probed.
     */
    public boolean inCareOf(Authentication staff, String patientId) {   // public: SpEL in @PreAuthorize only calls public methods
        return patient(patientId).map(p -> p.doctor().equals(staff.getName()) || p.ward().equals(NURSE_WARD.get(staff.getName()))).orElse(false);
    }
}
