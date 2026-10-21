package com.mediqo.wards;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.matchesPattern;
import static org.hamcrest.Matchers.nullValue;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class WardContractTest extends ApiTest {

    @Test
    void aDoctorReadsTheirPatientsNotes() throws Exception {
        notes("dr.sharma", "P-1001").andExpect(status().isOk())
                .andExpect(jsonPath("$[0].writtenBy").value("dr.sharma")).andExpect(jsonPath("$[0].text").value(matchesPattern("Chest pain.*")));
    }

    @Test
    void aNurseReadsNotesOfPatientsOnTheirWard() throws Exception {
        notes("nurse.ritu", "P-1002").andExpect(status().isOk());
        notes("nurse.joseph", "P-2001").andExpect(status().isOk());
    }

    @Test
    void aDoctorPrescribesForTheirPatient() throws Exception {
        prescribe("dr.bose", "P-2001", "{\"drug\":\" Paracetamol \",\"doseMg\":500,\"timesPerDay\":3,\"days\":5}").andExpect(status().isCreated())
                .andExpect(header().string("Location", matchesPattern("/patients/P-2001/prescriptions/RX-[0-9a-f]{8}")))
                .andExpect(jsonPath("$.drug").value("Paracetamol")).andExpect(jsonPath("$.prescribedBy").value("dr.bose"));
    }

    @Test
    void everyoneSeesTodaysAppointmentsButOnlyCliniciansSeeTheReason() throws Exception {
        today("reception.anu").andExpect(status().isOk()).andExpect(jsonPath("$[*].patient", contains("Kavya Menon", "Lakshmi Pillai")))
                .andExpect(jsonPath("$[0].reason").value(nullValue()));
        today("nurse.ritu").andExpect(jsonPath("$[0].reason").value("Cardiology follow-up"));
    }

    @Test
    void aBadPrescriptionIs400() throws Exception {
        prescribe("dr.sharma", "P-1001", "{\"drug\":\"\",\"doseMg\":75,\"timesPerDay\":1,\"days\":30}").andExpect(status().isBadRequest());
        prescribe("dr.sharma", "P-1001", "{\"drug\":\"Aspirin\",\"doseMg\":0,\"timesPerDay\":1,\"days\":30}").andExpect(status().isBadRequest());
        prescribe("dr.sharma", "P-1001", "{\"drug\":\"Aspirin\",\"doseMg\":75,\"timesPerDay\":9,\"days\":30}").andExpect(status().isBadRequest());
        prescribe("dr.sharma", "P-1001", "{\"drug\":\"Aspirin\",\"timesPerDay\":1,\"days\":30}").andExpect(status().isBadRequest());   // missing int
    }

    @Test
    void anUnknownPatientIsAnsweredLikeSomeoneElsesPatient() throws Exception {
        notes("dr.sharma", "P-9999").andExpect(status().isForbidden());
        notes("dr.sharma", "P-2001").andExpect(status().isForbidden());
    }
}
