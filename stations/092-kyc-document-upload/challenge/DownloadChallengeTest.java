package com.tijori.kyc;

import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: GET /kyc/{customerId}/documents/{documentId}/content downloads a document: the detected type, as an
 * attachment with its cleaned-up name, never shown inline. The owner and reviewers may; others 403; unknown 404.
 */
class DownloadChallengeTest extends ApiTest {

    ResultActions download(String user, long customer, String id) throws Exception {
        return mvc.perform(get("/kyc/{c}/documents/{d}/content", customer, id).with(httpBasic(user, password(user))));
    }

    @Test
    void theOwnerAndAReviewerDownloadItAsAnAttachment() throws Exception {
        upload("asha", 1, "PAN", "../../pan card.pdf", "image/png", PDF);
        String id = store.list(1).getFirst().id();
        download("asha", 1, id).andExpect(status().isOk()).andExpect(content().contentType("application/pdf")).andExpect(content().bytes(PDF))
                .andExpect(header().string("Content-Disposition", "attachment; filename=\"pan_card.pdf\""))
                .andExpect(header().string("X-Content-Type-Options", "nosniff"));
        download("kavya", 1, id).andExpect(status().isOk());
    }

    @Test
    void othersAre403AndUnknownDocumentsAre404() throws Exception {
        upload("asha", 1, "PAN", "pan.pdf", "application/pdf", PDF);
        String id = store.list(1).getFirst().id();
        download("rohan", 1, id).andExpect(status().isForbidden());
        download("rohan", 2, id).andExpect(status().isNotFound());   // Asha's document through Rohan's own path
        download("asha", 1, "00000000-0000-0000-0000-000000000000").andExpect(status().isNotFound());
        download("asha", 1, "..%2F..%2Fetc%2Fpasswd").andExpect(status().is4xxClientError());   // refused (400) before any lookup
    }
}
