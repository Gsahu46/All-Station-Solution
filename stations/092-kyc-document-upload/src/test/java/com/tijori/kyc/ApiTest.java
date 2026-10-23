package com.tijori.kyc;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import org.springframework.util.FileSystemUtils;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;

/** Shared setup: the whole app with its own storage folder, emptied before each test, and sample files. */
@SpringBootTest(properties = "tijori.storage-dir=target/test-storage/kyc")
@AutoConfigureMockMvc
abstract class ApiTest {

    static final byte[] PDF = bytes("%PDF-1.7\n1 0 obj\n");
    static final byte[] PNG = {(byte) 0x89, 'P', 'N', 'G', 0x0D, 0x0A, 0x1A, 0x0A, 0, 0, 0, 13};
    static final byte[] JPEG = {(byte) 0xFF, (byte) 0xD8, (byte) 0xFF, (byte) 0xE0, 0, 16};
    static final byte[] EXE = bytes("MZ\u0090\u0000 this program cannot be run in DOS mode");

    @Autowired
    MockMvc mvc;
    @Autowired
    DocumentStore store;

    @BeforeEach
    void emptyStorage() throws Exception {
        store.clear();
        FileSystemUtils.deleteRecursively(store.root().resolve("1"));
        FileSystemUtils.deleteRecursively(store.root().resolve("2"));
    }

    static byte[] bytes(String s) {
        return s.getBytes(java.nio.charset.StandardCharsets.ISO_8859_1);
    }

    static String password(String user) {
        return user + "-demo-pass";
    }

    ResultActions upload(String user, long customer, String type, String fileName, String contentType, byte[] content) throws Exception {
        return mvc.perform(multipart("/kyc/{id}/documents", customer).file(new MockMultipartFile("file", fileName, contentType, content))
                .param("type", type).with(httpBasic(user, password(user))));
    }

    ResultActions list(String user, long customer) throws Exception {
        return mvc.perform(get("/kyc/{id}/documents", customer).with(httpBasic(user, password(user))));
    }

    long filesUnder(Path dir) throws Exception {
        try (var walk = Files.walk(dir)) {
            return walk.filter(Files::isRegularFile).count();
        }
    }
}
