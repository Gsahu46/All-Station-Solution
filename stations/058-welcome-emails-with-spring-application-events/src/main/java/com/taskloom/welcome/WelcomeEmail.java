package com.taskloom.welcome;

import org.springframework.web.util.HtmlUtils;

/**
 * The welcome email. The name is the user's own input: it is HTML-escaped in the body (a name like
 * "<script>" stays text) and stripped of line breaks in the subject (a header must stay one line).
 */
final class WelcomeEmail {

    private static final String TEMPLATE = """
            <!DOCTYPE html>
            <html lang="en"><head><meta charset="UTF-8"><title>Welcome to Taskloom</title></head>
            <body><p>Hi %s,</p><p>Welcome to Taskloom. Your first board is ready.</p></body></html>""";

    private WelcomeEmail() {
    }

    static MailGateway.Message to(String email, String name) {
        String subject = "Welcome to Taskloom, " + name.replaceAll("[\\r\\n]+", " ");
        return new MailGateway.Message(email, subject, "text/html; charset=UTF-8", TEMPLATE.formatted(HtmlUtils.htmlEscape(name, "UTF-8")));
    }
}
