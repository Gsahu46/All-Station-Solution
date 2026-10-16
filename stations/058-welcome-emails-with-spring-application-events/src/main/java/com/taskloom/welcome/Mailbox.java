package com.taskloom.welcome;

import org.springframework.stereotype.Component;

import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

/** Simulated email provider: "sending" records the message here. No email leaves the app. shortcut: in memory. */
@Component
class Mailbox implements MailGateway {

    private final List<Message> sent = new CopyOnWriteArrayList<>();

    @Override
    public void send(Message message) {
        sent.add(message);
    }

    List<Message> all() {
        return List.copyOf(sent);
    }

    void clear() {
        sent.clear();
    }
}
