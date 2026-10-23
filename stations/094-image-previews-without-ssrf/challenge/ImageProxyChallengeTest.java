package com.chaupal.previews;

import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.json.JsonMapper;

import java.net.InetAddress;
import java.net.InetSocketAddress;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: GET /link-previews/{id}/image serves the preview's image through the server, so members' apps never
 * contact the site. The image is fetched with the same checks as the page: an og:image pointing at an internal
 * address is refused, and only images (image/*) of at most 1 MB are passed on.
 */
class ImageProxyChallengeTest extends ApiTest {

    HttpServer site;

    @BeforeEach
    void aSiteWithImages() throws Exception {
        site = HttpServer.create(new InetSocketAddress(InetAddress.getByName("127.0.0.2"), 0), 0);
        int port = site.getAddress().getPort();
        site.createContext("/good", x -> page(x, "/cover.png"));
        site.createContext("/evil", x -> page(x, "http://127.0.0.1:" + TestSites.PORT + "/latest/meta-data/"));
        site.createContext("/notimage", x -> page(x, "/cover.html"));
        site.createContext("/cover.png", x -> {
            byte[] png = {(byte) 0x89, 'P', 'N', 'G', 0x0D, 0x0A, 0x1A, 0x0A};
            x.getResponseHeaders().set("Content-Type", "image/png");
            x.sendResponseHeaders(200, png.length);
            x.getResponseBody().write(png);
            x.close();
        });
        site.createContext("/cover.html", x -> {
            x.getResponseHeaders().set("Content-Type", "text/html");
            x.sendResponseHeaders(200, 2);
            x.getResponseBody().write("hi".getBytes());
            x.close();
        });
        site.start();
        base = "http://127.0.0.2:" + port;
    }

    String base;

    static void page(com.sun.net.httpserver.HttpExchange x, String image) throws java.io.IOException {
        byte[] b = ("<title>t</title><meta property=\"og:image\" content=\"" + image + "\">").getBytes();
        x.getResponseHeaders().set("Content-Type", "text/html");
        x.sendResponseHeaders(200, b.length);
        x.getResponseBody().write(b);
        x.close();
    }

    @AfterEach
    void stop() {
        site.stop(0);
    }

    String previewId(String path) throws Exception {
        return JsonMapper.builder().build().readTree(preview(base + path).andReturn().getResponse().getContentAsString()).get("id").asString();
    }

    @Test
    void theImageComesThroughTheServer() throws Exception {
        read("meera", previewId("/good") + "/image").andExpect(status().isOk()).andExpect(content().contentType("image/png"));
    }

    @Test
    void anImagePointingInsideIsRefusedAndSoIsSomethingElse() throws Exception {
        read("meera", previewId("/evil") + "/image").andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.detail").value("This address cannot be previewed"));
        read("meera", previewId("/notimage") + "/image").andExpect(status().isUnprocessableContent());
        read("dev", previewId("/good") + "/image").andExpect(status().isNotFound());
    }
}
