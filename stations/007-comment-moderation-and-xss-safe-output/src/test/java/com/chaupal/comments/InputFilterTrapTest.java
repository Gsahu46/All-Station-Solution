package com.chaupal.comments;

import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.security.Principal;
import java.util.stream.Collectors;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/**
 * The first test written for this station: it reproduces the attack before the fix.
 * Two well-known payloads against a "remove the script tags from the input" defence.
 */
@Import(InputFilterTrapTest.FilteringController.class)
class InputFilterTrapTest extends ApiTest {

    static final String IMG = "<img src=x onerror=alert(document.cookie)>";
    static final String NESTED = "<scr<script>ipt>alert(1)</script>";

    /** The "before" code: strip <script> tags on the way in, then put the text into HTML as-is. Kept only in tests. */
    @RestController
    static class FilteringController {
        private final CommentService service;

        FilteringController(CommentService service) {
            this.service = service;
        }

        @PostMapping("/naive/posts/{postId}/comments")
        Comment add(Principal user, @PathVariable long postId, @RequestBody CommentRequest r) {
            String cleaned = r.text().replaceAll("(?i)<script>", "").replaceAll("(?i)</script>", "");
            return service.add(user.getName(), postId, cleaned);
        }

        @GetMapping(value = "/naive/posts/{postId}/comments", produces = MediaType.TEXT_HTML_VALUE)
        String html(Principal user, @PathVariable long postId) {
            return service.list(postId, user.getName()).stream()
                    .map(c -> "<li><b>" + c.author() + "</b> <p>" + c.text() + "</p></li>")
                    .collect(Collectors.joining("\n", "<ul>\n", "\n</ul>"));
        }
    }

    @Test
    void theFilterMissesAnImageTagAndRebuildsTheScriptTagItRemoved() throws Exception {
        for (String payload : new String[]{IMG, NESTED}) {
            mvc.perform(post("/naive/posts/1/comments").with(httpBasic("ravi", "ravi-demo-pass"))
                    .contentType(MediaType.APPLICATION_JSON).content(body(payload)));
        }
        String page = mvc.perform(get("/naive/posts/1/comments").with(httpBasic("asha", "asha-demo-pass")).accept(MediaType.TEXT_HTML))
                .andReturn().getResponse().getContentAsString();
        assertThat(page).contains("<img src=x onerror=alert(document.cookie)>"); // not a <script>, so the filter ignores it
        assertThat(page).contains("<script>alert(1)");                           // removing the inner tag joined the outer one
    }

    @Test
    void encodingOnOutputTurnsBothIntoHarmlessText() throws Exception {
        comment("ravi", 1, IMG);
        comment("ravi", 1, NESTED);
        String page = html(1);
        assertThat(page).contains("&lt;img src=x onerror=alert(document.cookie)&gt;");
        assertThat(page).contains("&lt;scr&lt;script&gt;ipt&gt;alert(1)&lt;/script&gt;");
        assertThat(page).doesNotContain("<img").doesNotContain("<script").doesNotContain("<scr<");
    }
}
