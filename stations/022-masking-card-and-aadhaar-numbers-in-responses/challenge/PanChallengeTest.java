package com.tijori.profiles;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/** Challenge 1: profiles gain a PAN (ABCDE1234F for Asha, made up), shown as XXXXXX234F. */
class PanChallengeTest extends ApiTest {

    @Test
    void thePanIsMaskedLikeEveryOtherNumber() throws Exception {
        String body = profileAs("asha", "c-1001")
                .andExpect(jsonPath("$.pan").value("XXXXXX234F"))
                .andReturn().getResponse().getContentAsString();
        assertThat(body).doesNotContain("ABCDE1234F");
        assertThat(Sensitive.pan("ABCDE1234F").toString()).isEqualTo("XXXXXX234F");
    }
}
