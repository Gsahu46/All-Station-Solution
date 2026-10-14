package com.citylibrary.loans;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Only the web layer: the controller, its validation and the error translation, with the service replaced by a mock.
 * It checks HTTP, not rules; the rules have their own test.
 */
@WebMvcTest({LoanController.class, LoanErrors.class})
class LoanControllerSliceTest {

    @Autowired
    MockMvc mvc;
    @MockitoBean
    LoanService service;

    @Test
    void aRefusalFromTheServiceBecomesA409WithItsReason() throws Exception {
        when(service.borrow("m-1", "b-1")).thenThrow(new LoanService.Refused(LoanService.Reason.UNPAID_FINE, "Fine unpaid."));
        mvc.perform(post("/loans").contentType(MediaType.APPLICATION_JSON).content("{\"memberId\":\"m-1\",\"bookId\":\"b-1\"}"))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.reason").value("UNPAID_FINE"))
                .andExpect(jsonPath("$.detail").value("Fine unpaid."));
    }

    @Test
    void anInvalidBodyNeverReachesTheService() throws Exception {
        mvc.perform(post("/loans").contentType(MediaType.APPLICATION_JSON).content("{\"memberId\":\" \"}"))
                .andExpect(status().isBadRequest());
        verifyNoInteractions(service);
    }
}
