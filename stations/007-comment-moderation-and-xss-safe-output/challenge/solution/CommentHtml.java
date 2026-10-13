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
                    .append(bold(htmlEscape(c.text()))).append("</p></li>\n");
        }
        return html.append("</ul>\n").toString();
    }

    /**
     * Challenge 1. Runs on text that is already encoded, so the only tag that can appear is the one we add.
     * Formatting first and encoding second would encode our own <strong> too; trusting user tags would undo the station.
     */
    static String bold(String encoded) {
        return encoded.replaceAll("\\*\\*([^*\\s][^*]*?)\\*\\*", "<strong>$1</strong>");
    }
}
