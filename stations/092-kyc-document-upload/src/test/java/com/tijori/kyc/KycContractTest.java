package com.tijori.kyc;

import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.security.MessageDigest;
import java.util.HexFormat;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class KycContractTest extends ApiTest {

    @Test
    void aDocumentIsStoredWithItsDetectedTypeSizeAndHash() throws Exception {
        upload("asha", 1, "PAN", "pan-card.pdf", "application/pdf", PDF).andExpect(status().isCreated())
                .andExpect(jsonPath("$.customerId").value(1)).andExpect(jsonPath("$.type").value("PAN"))
                .andExpect(jsonPath("$.fileName").value("pan-card.pdf")).andExpect(jsonPath("$.contentType").value("application/pdf"))
                .andExpect(jsonPath("$.sizeBytes").value(PDF.length))
                .andExpect(jsonPath("$.sha256").value(HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(PDF))));
        String id = store.list(1).getFirst().id();
        assertThat(Files.readAllBytes(store.root().resolve("1").resolve(id))).isEqualTo(PDF);
    }

    @Test
    void theTypeComesFromTheBytesNotTheHeader() throws Exception {
        upload("asha", 1, "PASSPORT", "passport.pdf", "application/pdf", PNG).andExpect(status().isCreated()).andExpect(jsonPath("$.contentType").value("image/png"));
        upload("asha", 1, "VOTER_ID", "voter", "application/octet-stream", JPEG).andExpect(status().isCreated()).andExpect(jsonPath("$.contentType").value("image/jpeg"));
        list("asha", 1).andExpect(status().isOk()).andExpect(jsonPath("$.length()").value(2)).andExpect(jsonPath("$[1].fileName").value("voter"));
    }

    @Test
    void badUploadsAre400AndUnknownCustomersAre404() throws Exception {
        upload("asha", 1, "PAN", "empty.pdf", "application/pdf", new byte[0]).andExpect(status().isBadRequest()).andExpect(jsonPath("$.detail").value("The file is empty"));
        upload("asha", 1, "AADHAAR", "a.pdf", "application/pdf", PDF).andExpect(status().isBadRequest());
        mvc.perform(multipart("/kyc/{id}/documents", 1).param("type", "PAN").with(httpBasic("asha", password("asha")))).andExpect(status().isBadRequest());
        list("kavya", 99).andExpect(status().isNotFound()).andExpect(jsonPath("$.detail").value("No such customer"));
        assertThat(store.list(1)).isEmpty();
    }
}
