package com.mediqo.reminders;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

/** Shared setup: the whole app through MockMvc. Appointment 501: Asha, prefers Hindi; 502: Ravi, prefers English. */
@SpringBootTest
@AutoConfigureMockMvc
abstract class ApiTest {

    static final String ASHA_HI = "नमस्ते Asha, डॉ. Mehta के साथ आपका अपॉइंटमेंट 20 अक्टूबर 2026 को 10:30 बजे है। कृपया क्लिनिक में ₹1,23,456.50 का भुगतान करें।";
    static final String ASHA_EN = "Hello Asha, your appointment with Dr Mehta is on 20 October 2026 at 10:30. Please pay ₹1,23,456.50 at the clinic.";

    @Autowired
    MockMvc mvc;

    ResultActions reminder(long id, String lang, String acceptLanguage) throws Exception {
        MockHttpServletRequestBuilder request = get("/appointments/{id}/reminder", id);
        if (lang != null) {
            request = request.param("lang", lang);
        }
        if (acceptLanguage != null) {
            request = request.header("Accept-Language", acceptLanguage);
        }
        return mvc.perform(request);
    }
}
