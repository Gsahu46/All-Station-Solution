package com.chaupal.feed;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Size;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
class FeedController {

    private final Feed feed;

    FeedController(Feed feed) {
        this.feed = feed;
    }

    /** Newest first. Pass the response's nextCursor to get the following page; null means the end. */
    @GetMapping("/feed")
    Feed.Page feed(@RequestParam(required = false) @Size(max = 100) String cursor,
                   @RequestParam(defaultValue = "20") @Min(1) @Max(50) int limit) {
        return feed.page(cursor == null ? null : Cursor.decode(cursor), limit);
    }
}
