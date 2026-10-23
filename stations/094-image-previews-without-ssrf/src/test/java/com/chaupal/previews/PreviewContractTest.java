package com.chaupal.previews;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.json.JsonMapper;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class PreviewContractTest extends ApiTest {

    @Test
    void aPublicPageGivesATitleDescriptionAndImageLink() throws Exception {
        String body = preview(TestSites.url("news.example", "/article")).andExpect(status().isCreated())
                .andExpect(jsonPath("$.url").value(TestSites.url("news.example", "/article")))
                .andExpect(jsonPath("$.title").value("Monsoon reaches Kerala early"))
                .andExpect(jsonPath("$.description").value("Rain in Kochi & Thiruvananthapuram."))
                .andExpect(jsonPath("$.imageUrl").value(TestSites.url("news.example", "/img/cover.jpg")))
                .andReturn().getResponse().getContentAsString();
        String id = JsonMapper.builder().build().readTree(body).get("id").asString();
        read("meera", id).andExpect(status().isOk()).andExpect(jsonPath("$.title").value("Monsoon reaches Kerala early"));
    }

    @Test
    void aSafeRedirectIsFollowed() throws Exception {
        preview(TestSites.url("news.example", "/to-article")).andExpect(status().isCreated())
                .andExpect(jsonPath("$.imageUrl").value(TestSites.url("news.example", "/img/cover.jpg")));
    }

    @Test
    void whatCannotBePreviewedIsSaidPlainly() throws Exception {
        preview(TestSites.url("news.example", "/image.png")).andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.detail").value("The link is not a web page"));
        preview(TestSites.url("news.example", "/gone")).andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.detail").value("The page answered 404"));
        preview(TestSites.url("nosuch.example", "/")).andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.detail").value("No such host"));
        preview(TestSites.url("news.example", "/loop")).andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.detail").value("Too many redirects"));
        preview("not a link").andExpect(status().isBadRequest());
        read("meera", "00000000-0000-0000-0000-000000000000").andExpect(status().isNotFound());
    }
}
