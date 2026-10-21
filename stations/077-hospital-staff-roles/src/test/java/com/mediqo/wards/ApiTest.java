package com.mediqo.wards;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import java.util.Map;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/** Shared setup: the whole app with its security; staff sign in with HTTP Basic, as the ward app does. */
@SpringBootTest
@AutoConfigureMockMvc
abstract class ApiTest {

    static final Map<String, String> PASSWORDS = Map.of("reception.anu", "anu-demo-pass", "nurse.ritu", "ritu-demo-pass",
            "nurse.joseph", "joseph-demo-pass", "dr.sharma", "sharma-demo-pass", "dr.bose", "bose-demo-pass");

    @Autowired
    MockMvc mvc;

    ResultActions notes(String staff, String patientId) throws Exception {
        return mvc.perform(get("/patients/{id}/notes", patientId).with(httpBasic(staff, PASSWORDS.get(staff))));
    }

    ResultActions today(String staff) throws Exception {
        return mvc.perform(get("/appointments/today").with(httpBasic(staff, PASSWORDS.get(staff))));
    }

    ResultActions prescribe(String staff, String patientId, String json) throws Exception {
        return mvc.perform(post("/patients/{id}/prescriptions", patientId).with(httpBasic(staff, PASSWORDS.get(staff)))
                .contentType(MediaType.APPLICATION_JSON).content(json));
    }

    static final String ASPIRIN = "{\"drug\":\"Aspirin\",\"doseMg\":75,\"timesPerDay\":1,\"days\":30}";
}
