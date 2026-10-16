package com.tijori.notifications;

import org.springframework.stereotype.Component;

import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * Simulated providers: "sending" records the message here. No SMS, email or push leaves this app.
 * shortcut: in memory and unbounded, fine for a demo; a real app hands messages to a provider's API.
 */
@Component
class Outbox {

    record Sent(Model.ChannelName channel, String to, String text) {
    }

    private final List<Sent> sent = new CopyOnWriteArrayList<>();

    void record(Model.ChannelName channel, String to, String text) {
        sent.add(new Sent(channel, to, text));
    }

    List<Sent> all() {
        return List.copyOf(sent);
    }

    void clear() {
        sent.clear();
    }
}
