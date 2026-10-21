package com.mediqo.wards;

import org.springframework.security.core.Authentication;
import org.springframework.stereotype.Component;

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

    Optional<Patient> patient(String id) {
        return Optional.ofNullable(patients.get(id));
    }

    /**
     * Least privilege, per patient: a doctor for their own patients, a nurse for patients on their ward. Used in
     * {@code @PreAuthorize}; an unknown patient is "not in your care" too, so ids cannot be probed.
     */
    boolean inCareOf(Authentication staff, String patientId) {
        return patient(patientId).map(p -> p.doctor().equals(staff.getName()) || p.ward().equals(NURSE_WARD.get(staff.getName()))).orElse(false);
    }
}
