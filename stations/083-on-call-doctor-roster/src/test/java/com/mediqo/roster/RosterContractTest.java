package com.mediqo.roster;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class RosterContractTest extends ApiTest {

    @Test
    void aDoctorGoesOffCallWhileAnotherStaysOn() throws Exception {
        offCall("cardiology", "dr.sharma").andExpect(status().isOk()).andExpect(jsonPath("$.onCall").value(false))
                .andExpect(jsonPath("$.onCallInWard").value(1));
    }

    @Test
    void theLastDoctorOnCallCannotGo() throws Exception {
        offCall("cardiology", "dr.sharma");
        offCall("cardiology", "dr.iyer").andExpect(status().isConflict()).andExpect(jsonPath("$.detail").value("Cardiology needs at least 1 doctor on call"));
        org.assertj.core.api.Assertions.assertThat(onCall("cardiology")).isEqualTo(1);
    }

    @Test
    void unknownWardsAndDoctorsAre404AndBadNamesAre400() throws Exception {
        offCall("neurology", "dr.sharma").andExpect(status().isNotFound()).andExpect(jsonPath("$.detail").value("No such ward"));
        offCall("cardiology", "dr.bose").andExpect(status().isNotFound()).andExpect(jsonPath("$.detail").value("No such doctor on this ward"));
        offCall("cardiology", "Sharma").andExpect(status().isBadRequest());
        offCall("cardiology", "dr.sharma' OR '1'='1").andExpect(status().isBadRequest());
    }
}
