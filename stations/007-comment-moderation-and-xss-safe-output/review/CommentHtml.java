package com.chaupal.comments;

import java.util.List;

/** Comments as an HTML fragment. Text is already sanitised when it is saved (see CommentService), so no escaping needed here. */
final class CommentHtml {

    private CommentHtml() {
    }

    static String render(List<Comment> comments) {
        StringBuilder html = new StringBuilder("<ul class=\"comments\">\n");
        for (Comment c : comments) {
            html.append("  <li><b>").append(c.author()).append("</b> <p>").append(c.text()).append("</p></li>\n");
        }
        return html.append("</ul>\n").toString();
    }
}
