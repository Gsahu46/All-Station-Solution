package com.taskloom.webinars;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * Challenge 2: each session also shows "viewerEndTime" (start plus the duration, in the viewer's zone) and
 * "viewerDayShift": the viewer's calendar date minus the host's (-1 means "the evening before" for the viewer).
 */
class ViewerDayChallengeTest extends ApiTest {

    @Test
    void theViewerSeesTheirOwnDayAndEnd() throws Exception {
        String url = created(webinar("2026-11-05T10:00", "Asia/Kolkata", ""));
        mvc.perform(get(url).param("viewerZone", "America/Los_Angeles"))
                .andExpect(jsonPath("$.sessions[0].viewerEndTime").value("2026-11-04T21:30:00-08:00"))
                .andExpect(jsonPath("$.sessions[0].viewerDayShift").value(-1));
        mvc.perform(get(url).param("viewerZone", "Pacific/Auckland"))
                .andExpect(jsonPath("$.sessions[0].viewerTime").value("2026-11-05T17:30:00+13:00"))
                .andExpect(jsonPath("$.sessions[0].viewerDayShift").value(0));
        mvc.perform(get(url)).andExpect(jsonPath("$.sessions[0].viewerDayShift").value(0));
    }
}
