package com.taskloom.welcome;

/** Where email goes. One implementation here, the simulated mailbox; a real one would call an email provider. */
interface MailGateway {

    record Message(String to, String subject, String contentType, String html) {
    }

    void send(Message message);
}
