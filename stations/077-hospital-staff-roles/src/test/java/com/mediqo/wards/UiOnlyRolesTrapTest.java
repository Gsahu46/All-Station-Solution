package com.mediqo.wards;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Written first. In the old system the roles lived in the ward app's menu: reception never saw a "Notes" button. The
 * API behind it let every signed-in user call every endpoint. Each test shows what the old menu hid, then calls the
 * endpoint directly, as anyone with the URL can.
 */
class UiOnlyRolesTrapTest extends ApiTest {

    /** The old ward app's menu, as it was: the only place roles were checked. */
    static List<String> oldMenu(String role) {
        return switch (role) {
            case "RECEPTIONIST" -> List.of("Appointments");
            case "NURSE" -> List.of("Appointments", "Notes");
            default -> List.of("Appointments", "Notes", "Prescribe");
        };
    }

    @Test
    void receptionCouldReadClinicalNotesByCallingTheApi() throws Exception {
        assertThat(oldMenu("RECEPTIONIST")).doesNotContain("Notes");   // hidden on screen
        notes("reception.anu", "P-1001").andExpect(status().isForbidden());   // and now refused by the API
    }

    @Test
    void aNurseCouldPrescribeByCallingTheApi() throws Exception {
        assertThat(oldMenu("NURSE")).doesNotContain("Prescribe");
        prescribe("nurse.ritu", "P-1001", ASPIRIN).andExpect(status().isForbidden());
    }

    @Test
    void receptionCouldPrescribeToo() throws Exception {
        prescribe("reception.anu", "P-1001", ASPIRIN).andExpect(status().isForbidden());
    }

    @Test
    void theRightRoleForTheRightPatientWorks() throws Exception {
        // The control: a doctor, for her own patient.
        notes("dr.sharma", "P-1001").andExpect(status().isOk());
        prescribe("dr.sharma", "P-1001", ASPIRIN).andExpect(status().isCreated());
    }
}
