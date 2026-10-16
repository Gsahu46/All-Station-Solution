package com.tijori.notifications;

import org.junit.jupiter.api.Test;
import org.springframework.test.context.bean.override.mockito.MockitoSpyBean;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doCallRealMethod;
import static org.mockito.Mockito.doThrow;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: POST /notifications/{id}/retry delivers again only what FAILED, and answers the notification. A
 * customer must not get a second SMS because email was down. Nothing failed: 409. Unknown id: 404.
 */
class RetryChallengeTest extends ApiTest {

    @MockitoSpyBean
    EmailChannel email;

    @Test
    void onlyTheFailedChannelIsTriedAgain() throws Exception {
        doThrow(new IllegalStateException("email provider timed out")).doCallRealMethod().when(email).deliver(any(), any());
        String body = notify(debit(1, 149900)).andExpect(jsonPath(statusOf("EMAIL")).value("FAILED")).andReturn().getResponse().getContentAsString();
        long id = Long.parseLong(body.replaceAll("^\\{\"id\":(\\d+).*", "$1"));
        mvc.perform(post("/notifications/{id}/retry", id)).andExpect(status().isOk())
                .andExpect(jsonPath(statusOf("EMAIL")).value("SENT")).andExpect(jsonPath(statusOf("SMS")).value("SENT"));
        assertThat(outbox.all()).extracting(Outbox.Sent::channel).containsExactlyInAnyOrder(
                Model.ChannelName.SMS, Model.ChannelName.PUSH, Model.ChannelName.EMAIL);   // one SMS, not two
        mvc.perform(post("/notifications/{id}/retry", id)).andExpect(status().isConflict());
        mvc.perform(post("/notifications/{id}/retry", 999_999)).andExpect(status().isNotFound());
    }
}
