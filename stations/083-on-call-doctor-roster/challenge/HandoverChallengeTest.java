package com.mediqo.roster;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.ResultActions;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: POST /rosters/{ward}/handover {from, to}. The doctor taking over goes on call and the other goes off in
 * one transaction, so it works even when the ward is at its minimum. Repeating a done handover changes nothing.
 */
class HandoverChallengeTest extends ApiTest {

    ResultActions handover(String ward, String from, String to) throws Exception {
        return mvc.perform(post("/rosters/{ward}/handover", ward).contentType(MediaType.APPLICATION_JSON)
                .content("{\"from\":\"" + from + "\",\"to\":\"" + to + "\"}"));
    }

    @Test
    void theLastDoctorOnCallCanHandOver() throws Exception {
        offCall("cardiology", "dr.sharma").andExpect(status().isOk());   // dr.iyer is now the only one on call
        handover("cardiology", "dr.iyer", "dr.menon").andExpect(status().isOk()).andExpect(jsonPath("$.onCallInWard").value(1));
        assertThat(jdbc.sql("SELECT doctor FROM roster WHERE ward = 'cardiology' AND on_call").query(String.class).list()).containsExactly("dr.menon");
        assertThat(jdbc.sql("SELECT doctor || ' ' || went FROM roster_changes WHERE doctor <> 'dr.sharma' ORDER BY id").query(String.class).list())
                .containsExactly("dr.menon on", "dr.iyer off");
    }

    @Test
    void aRepeatedHandoverChangesNothingAndAWrongOneIs409Or404() throws Exception {
        handover("cardiology", "dr.iyer", "dr.menon").andExpect(status().isOk());
        handover("cardiology", "dr.iyer", "dr.menon").andExpect(status().isOk());
        assertThat(jdbc.sql("SELECT count(*) FROM roster_changes").query(Integer.class).single()).isEqualTo(2);
        handover("cardiology", "dr.sharma", "dr.iyer").andExpect(status().isOk());       // dr.sharma off, dr.iyer back on
        handover("cardiology", "dr.sharma", "dr.sharma").andExpect(status().isBadRequest());
        handover("cardiology", "dr.iyer", "dr.bose").andExpect(status().isNotFound());   // dr.bose is on another ward
        handover("cardiology", "dr.menon", "dr.sharma").andExpect(status().isOk());
        handover("cardiology", "dr.iyer", "dr.sharma").andExpect(status().isConflict()); // nothing to hand over: dr.sharma is already on
    }
}
