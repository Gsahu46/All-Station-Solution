package com.chaupal.threads;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * The first test written for this station: it reproduces the crash before the fix.
 * Post 2 is one reply chain, 100,000 comments deep.
 */
class UnboundedRecursionTrapTest extends ApiTest {

    @Autowired
    CommentStore store;

    /** The "before" code: nest every reply inside its parent, as deep as the data goes. Kept only in tests. */
    static Node naive(Comment c, Map<Long, List<Comment>> children) {
        List<Node> replies = children.getOrDefault(c.id(), List.of()).stream().map(r -> naive(r, children)).toList();
        return new Node(c.id(), c.author(), c.text(), c.createdAt(), replies, 0);
    }

    @Test
    void recursionWithoutALimitOverflowsTheStackOnADeepThread() {
        List<Comment> chain = store.forPost(2).orElseThrow();
        Map<Long, List<Comment>> children = chain.stream().filter(c -> c.parentId() != null)
                .collect(Collectors.groupingBy(Comment::parentId));
        Comment root = chain.getFirst();
        assertThatThrownBy(() -> naive(root, children)).isInstanceOf(StackOverflowError.class); // a 500 for every reader
    }

    @Test
    void theRealEndpointStopsAtTheDepthLimitAndCountsWhatIsBelow() throws Exception {
        mvc.perform(get("/posts/2/comment-tree").param("maxDepth", "3"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.comments[0].text").value("Reply 0"))
                .andExpect(jsonPath("$.comments[0].replies[0].replies[0].text").value("Reply 2"))
                .andExpect(jsonPath("$.comments[0].replies[0].replies[0].replies").isEmpty())
                .andExpect(jsonPath("$.comments[0].replies[0].replies[0].moreReplies").value(99_997));
    }
}
