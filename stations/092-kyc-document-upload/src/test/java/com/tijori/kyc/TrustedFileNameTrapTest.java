package com.tijori.kyc;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockMultipartFile;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Written first. The old upload did Files.write(uploads.resolve(file.getOriginalFilename()), file.getBytes()) and
 * accepted whatever Content-Type the client sent: a name with ../ wrote outside the folder, a program sent as
 * application/pdf was stored as a PDF, and getBytes() held every upload whole in memory.
 */
class TrustedFileNameTrapTest extends ApiTest {

    @Test
    void theOldWayWroteOutsideTheFolderAndTrustedTheHeader() throws Exception {
        Path uploads = Files.createDirectories(Path.of("target/test-storage/old/uploads/1")).toRealPath();
        MockMultipartFile file = new MockMultipartFile("file", "../../escaped.pdf", "application/pdf", EXE);
        Path target = uploads.resolve(file.getOriginalFilename()).normalize();
        Files.write(target, file.getBytes());
        assertThat(target).exists();
        assertThat(target.startsWith(uploads)).isFalse();             // written two folders up
        assertThat(file.getContentType()).isEqualTo("application/pdf");   // and "a PDF", by the client's word
        Files.delete(target);
    }

    @Test
    void theApiKeepsEveryFileInsideItsFolderUnderItsOwnName() throws Exception {
        upload("asha", 1, "PAN", "../../escaped.pdf", "application/pdf", PDF).andExpect(status().isCreated())
                .andExpect(jsonPath("$.fileName").value("escaped.pdf"));
        Path customerDir = store.root().resolve("1");
        try (var files = Files.list(customerDir)) {
            assertThat(files.map(p -> p.getFileName().toString()).toList()).singleElement().asString().matches("[0-9a-f-]{36}");
        }
        assertThat(store.root().getParent().getParent().resolve("escaped.pdf")).doesNotExist();
    }

    @Test
    void theApiDecidesTheTypeFromTheBytes() throws Exception {
        upload("asha", 1, "PAN", "pan.pdf", "application/pdf", EXE).andExpect(status().isUnsupportedMediaType())
                .andExpect(jsonPath("$.detail").value("Only PDF, PNG and JPEG documents are accepted"));
        assertThat(store.list(1)).isEmpty();
        assertThat(Files.exists(store.root().resolve("1")) ? filesUnder(store.root().resolve("1")) : 0).isZero();
    }
}
