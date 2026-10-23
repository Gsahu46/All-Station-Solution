package com.tijori.kyc;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class KycSecurityTest extends ApiTest {

    @Test
    void withoutAValidSignInIt401s() throws Exception {
        mvc.perform(get("/kyc/1/documents")).andExpect(status().isUnauthorized()).andExpect(jsonPath("$.title").value("Sign-in required"));
        mvc.perform(get("/kyc/1/documents").with(httpBasic("asha", "wrong"))).andExpect(status().isUnauthorized());
    }

    @Test
    void oneCustomerCannotUploadForOrReadAnother() throws Exception {
        upload("asha", 1, "PAN", "pan.pdf", "application/pdf", PDF).andExpect(status().isCreated());
        list("rohan", 1).andExpect(status().isForbidden());
        upload("rohan", 1, "PAN", "pan.pdf", "application/pdf", PDF).andExpect(status().isForbidden());
        list("rohan", 2).andExpect(status().isOk()).andExpect(jsonPath("$.length()").value(0));
        assertThat(store.list(1)).hasSize(1);
    }

    @Test
    void aReviewerReadsAnyCustomerButUploadsForNone() throws Exception {
        upload("asha", 1, "PAN", "pan.pdf", "application/pdf", PDF);
        list("kavya", 1).andExpect(status().isOk()).andExpect(jsonPath("$[0].type").value("PAN"));
        upload("kavya", 1, "PAN", "pan.pdf", "application/pdf", PDF).andExpect(status().isForbidden());
    }

    /** A different small PDF each time, so no two uploads are the same file. */
    static byte[] pdf(int n) {
        return bytes("%PDF-1.7\n% " + n + "\n");
    }

    @Test
    void maliciousFileNamesBecomeHarmlessLabels() throws Exception {
        upload("asha", 1, "PAN", "..\\..\\windows\\win.ini", "application/pdf", pdf(1)).andExpect(jsonPath("$.fileName").value("win.ini"));
        upload("asha", 1, "PAN", ".htaccess", "application/pdf", pdf(2)).andExpect(jsonPath("$.fileName").value("htaccess"));
        upload("asha", 1, "PAN", "..", "application/pdf", pdf(3)).andExpect(jsonPath("$.fileName").value("document"));
        upload("asha", 1, "PAN", "pan<script>.pdf", "application/pdf", pdf(4)).andExpect(jsonPath("$.fileName").value("pan_script_.pdf"));
        upload("asha", 1, "PAN", "a".repeat(300) + ".pdf", "application/pdf", pdf(5)).andExpect(jsonPath("$.fileName").value("a".repeat(100)));
        upload("asha", 1, "PAN", "pan.pdf\u0000.exe", "application/pdf", pdf(6)).andExpect(jsonPath("$.fileName").value("pan.pdf_.exe"));
        assertThat(filesUnder(store.root().resolve("1"))).isEqualTo(6);
        assertThat(filesUnder(store.root())).isEqualTo(6);   // nothing anywhere else in storage
    }
}
