package com.dakroute.partner;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/** Shared setup: the whole app through MockMvc, and the partner's payload as they really send it. */
@SpringBootTest
@AutoConfigureMockMvc
abstract class ApiTest {

    /** Out for delivery in Pune at 09:15 India time, with two fields the partner added this week. */
    static final String PARTNER_PAYLOAD = """
            {"awb_number":"DKR100000001IN","status_code":"OFD","event_time":"2026-10-14 09:15:00",
             "location":{"city_name":"Pune","pin_code":"411001","hub_id":"PNQ-07"},
             "promised_by":"2026-10-14T18:00:00+05:30",
             "rider_phone":"98XXXXXX21","temperature_c":31.5}""";

    @Autowired
    MockMvc mvc;

    ResultActions update(String json) throws Exception {
        return mvc.perform(post("/partner/delivery-updates").contentType(MediaType.APPLICATION_JSON).content(json));
    }
}
