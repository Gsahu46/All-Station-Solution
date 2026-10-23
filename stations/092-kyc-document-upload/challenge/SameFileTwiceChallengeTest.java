package com.tijori.kyc;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: the app retries an upload that timed out. The same bytes for the same customer and type are not
 * stored again: 200 with the document already there (same id). Different bytes, or another type, are a new document.
 */
class SameFileTwiceChallengeTest extends ApiTest {

    @Test
    void theSameBytesAreOneDocument() throws Exception {
        String first = upload("asha", 1, "PAN", "pan.pdf", "application/pdf", PDF).andExpect(status().isCreated()).andReturn().getResponse().getContentAsString();
        String again = upload("asha", 1, "PAN", "pan-again.pdf", "application/pdf", PDF).andExpect(status().isOk()).andReturn().getResponse().getContentAsString();
        assertThat(again).isEqualTo(first);
        assertThat(filesUnder(store.root().resolve("1"))).isOne();
    }

    @Test
    void otherBytesOrAnotherTypeAreNewDocuments() throws Exception {
        upload("asha", 1, "PAN", "pan.pdf", "application/pdf", PDF).andExpect(status().isCreated());
        upload("asha", 1, "PASSPORT", "pan.pdf", "application/pdf", PDF).andExpect(status().isCreated());
        upload("asha", 1, "PAN", "pan.png", "image/png", PNG).andExpect(status().isCreated()).andExpect(jsonPath("$.contentType").value("image/png"));
        assertThat(store.list(1)).hasSize(3);
    }
}
