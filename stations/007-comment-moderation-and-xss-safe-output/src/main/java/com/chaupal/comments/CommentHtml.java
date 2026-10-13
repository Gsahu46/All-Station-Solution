package com.chaupal.comments;

import java.util.List;

import static org.springframework.web.util.HtmlUtils.htmlEscape;

/**
 * The comments as an HTML fragment, for the web page that embeds them. Every piece of user text goes through
 * htmlEscape: < > & " ' become &lt; &gt; &amp; &quot; &#39;, so the browser shows them as characters and never
 * reads them as tags or attributes. Encode at the moment of output, for the format being output.
 */
final class CommentHtml {

    private CommentHtml() {
    }

    static String render(List<Comment> comments) {
        StringBuilder html = new StringBuilder("<ul class=\"comments\">\n");
        for (Comment c : comments) {
            html.append("  <li><b>").append(htmlEscape(c.author())).append("</b> <p>")
                    .append(htmlEscape(c.text())).append("</p></li>\n");
        }
        return html.append("</ul>\n").toString();
    }
}
