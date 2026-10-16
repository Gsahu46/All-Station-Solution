package com.taskloom.webinars;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The HTTP contract: create and view in any zone; daylight saving, month ends; 400, 422 and 404. */
class WebinarContractTest extends ApiTest {

    @Test
    void createdInTheHostZoneAndShownInAnyOther() throws Exception {
        String url = create(webinar("2026-11-05T10:00", "Asia/Kolkata", "")).andExpect(status().isCreated())
                .andExpect(header().string("Location", org.hamcrest.Matchers.matchesPattern("/webinars/[0-9]+")))
                .andExpect(jsonPath("$.viewerZone").value("Asia/Kolkata")).andExpect(jsonPath("$.sessions[0].viewerTime").value("2026-11-05T10:00:00+05:30"))
                .andReturn().getResponse().getHeader("Location");
        mvc.perform(get(url).param("viewerZone", "America/Los_Angeles"))
                .andExpect(jsonPath("$.sessions[0].viewerTime").value("2026-11-04T20:30:00-08:00"));   // the evening before
        mvc.perform(get(url)).andExpect(jsonPath("$.viewerZone").value("Asia/Kolkata"));
    }

    @Test
    void theFirstMinuteThatCountsIsTheClocks() throws Exception {
        // Now is 11:30 in India. 11:30 has started; 11:31 has not.
        create(webinar("2026-10-16T11:30", "Asia/Kolkata", "")).andExpect(status().isUnprocessableContent());
        create(webinar("2026-10-16T11:31", "Asia/Kolkata", "")).andExpect(status().isCreated());
    }

    @Test
    void aTimeTheClocksSkipIsRefused() throws Exception {
        create(webinar("2027-03-14T02:30", "America/New_York", "")).andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.detail").value("2027-03-14T02:30 does not exist in America/New_York: the clocks skip it for daylight saving."));
        create(webinar("2027-03-28T01:30", "Europe/London", "")).andExpect(status().isUnprocessableContent());
    }

    @Test
    void aTimeThatHappensTwiceNeedsAnOffset() throws Exception {
        create(webinar("2026-11-01T01:30", "America/New_York", "")).andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.detail").value(org.hamcrest.Matchers.containsString("-04:00 and -05:00")));
        create(webinar("2026-11-01T01:30", "America/New_York", ",\"offset\":\"-05:00\"")).andExpect(status().isCreated())
                .andExpect(jsonPath("$.sessions[0].startsAt").value("2026-11-01T06:30:00Z"));
        create(webinar("2026-11-01T01:30", "America/New_York", ",\"offset\":\"+05:30\"")).andExpect(status().isUnprocessableContent());
    }

    @Test
    void monthlyFromThe31stKeepsToTheMonthEnd() throws Exception {
        create(webinar("2027-01-31T10:00", "Asia/Kolkata", ",\"repeat\":\"MONTHLY\",\"sessions\":4")).andExpect(status().isCreated())
                .andExpect(jsonPath("$.sessions[*].hostTime", contains("2027-01-31T10:00:00+05:30", "2027-02-28T10:00:00+05:30",
                        "2027-03-31T10:00:00+05:30", "2027-04-30T10:00:00+05:30")));
        create(webinar("2028-01-31T10:00", "Asia/Kolkata", ",\"repeat\":\"MONTHLY\",\"sessions\":2"))
                .andExpect(jsonPath("$.sessions[1].hostTime").value("2028-02-29T10:00:00+05:30"));   // a leap year
    }

    @Test
    void lastFridayOfEachMonth() throws Exception {
        create(webinar("2026-10-30T16:00", "Asia/Kolkata", ",\"repeat\":\"MONTHLY_LAST_WEEKDAY\",\"sessions\":3")).andExpect(status().isCreated())
                .andExpect(jsonPath("$.sessions[*].hostTime", contains("2026-10-30T16:00:00+05:30", "2026-11-27T16:00:00+05:30", "2026-12-25T16:00:00+05:30")));
        create(webinar("2026-10-23T16:00", "Asia/Kolkata", ",\"repeat\":\"MONTHLY_LAST_WEEKDAY\",\"sessions\":3"))
                .andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.detail").value("2026-10-23 is not the last FRIDAY of its month."));
    }

    @Test
    void brokenRequestsAre400() throws Exception {
        create(webinar("2026-11-05T10:00", "IST", "")).andExpect(status().isBadRequest()).andExpect(jsonPath("$.title").value("Unknown time zone"));
        create(webinar("2026-11-05T10:00", "+05:30", "")).andExpect(status().isBadRequest());
        create(webinar("05/11/2026 10:00", "Asia/Kolkata", "")).andExpect(status().isBadRequest());
        create(webinar("2026-11-05T10:00", "Asia/Kolkata", "").replace("60", "10")).andExpect(status().isBadRequest());   // under 15 minutes
        create(webinar("2026-11-05T10:00", "Asia/Kolkata", ",\"sessions\":13")).andExpect(status().isBadRequest());
        create(webinar("2026-11-05T10:00", "Asia/Kolkata", ",\"repeat\":\"DAILY\"")).andExpect(status().isBadRequest());
        create(webinar("2026-11-05T10:00", "Asia/Kolkata", ",\"sessions\":3")).andExpect(status().isUnprocessableContent());   // one-off with 3 sessions
        String url = created(webinar("2026-11-05T10:00", "Asia/Kolkata", ""));
        mvc.perform(get(url).param("viewerZone", "Mars/Olympus")).andExpect(status().isBadRequest());
    }

    @Test
    void unknownWebinarsAre404() throws Exception {
        mvc.perform(get("/webinars/999999")).andExpect(status().isNotFound()).andExpect(jsonPath("$.detail").value("No webinar 999999."));
    }
}
