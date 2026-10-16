package com.tijori.notifications;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Decides which channels a notice goes to and asks each one to deliver it. It knows no wording, no address format
 * and no provider: it depends on the Channel interface, and Spring hands it every Channel bean there is.
 */
@Service
class NotificationService {

    private static final Logger log = LoggerFactory.getLogger(NotificationService.class);

    record Notification(long id, long customerId, Model.NotificationType type, List<Model.Delivery> deliveries) {
    }

    private final List<Channel> channels;
    private final Customers customers;
    private final AtomicLong ids = new AtomicLong();
    private final Map<Long, Sent> sent = new ConcurrentHashMap<>();   // shortcut: in memory; a real service keeps a table

    private record Sent(Model.Customer customer, Model.Notice notice, Notification notification) {
    }

    NotificationService(List<Channel> channels, Customers customers) {
        this.channels = channels;
        this.customers = customers;
    }

    Notification send(Model.Customer customer, Model.Notice notice) {
        Model.Preferences prefs = customers.preferencesOf(customer.id());
        List<Model.Delivery> deliveries = new ArrayList<>();
        for (Channel channel : channels) {
            if (!notice.type().wants(channel.name(), prefs)) {
                deliveries.add(new Model.Delivery(channel.name(), Model.Status.SKIPPED, null, null));
                continue;
            }
            try {
                deliveries.add(channel.deliver(customer, notice));
            } catch (RuntimeException e) {
                // One channel failing must not stop the others: the SMS still goes when email is down.
                log.warn("{} delivery failed for customer {}", channel.name(), customer.id(), e);
                deliveries.add(new Model.Delivery(channel.name(), Model.Status.FAILED, null, null));
            }
        }
        deliveries.sort((a, b) -> a.channel().compareTo(b.channel()));
        Notification n = new Notification(ids.incrementAndGet(), customer.id(), notice.type(), deliveries);
        sent.put(n.id(), new Sent(customer, notice, n));
        return n;
    }

    /** Delivers again only what FAILED; every other channel keeps its first result, so nobody gets a second SMS. */
    synchronized Notification retry(long id) {
        Sent s = sent.get(id);
        if (s == null) {
            throw NotificationController.problem(HttpStatus.NOT_FOUND, "Notification not found", "No notification " + id + ".");
        }
        if (s.notification().deliveries().stream().noneMatch(d -> d.status() == Model.Status.FAILED)) {
            throw NotificationController.problem(HttpStatus.CONFLICT, "Nothing to retry", "No delivery of notification " + id + " failed.");
        }
        List<Model.Delivery> deliveries = new ArrayList<>();
        for (Model.Delivery d : s.notification().deliveries()) {
            deliveries.add(d.status() != Model.Status.FAILED ? d : attempt(channelNamed(d.channel()), s.customer(), s.notice()));
        }
        Notification n = new Notification(id, s.customer().id(), s.notice().type(), deliveries);
        sent.put(id, new Sent(s.customer(), s.notice(), n));
        return n;
    }

    private Channel channelNamed(Model.ChannelName name) {
        return channels.stream().filter(c -> c.name() == name).findFirst().orElseThrow();
    }

    private Model.Delivery attempt(Channel channel, Model.Customer customer, Model.Notice notice) {
        try {
            return channel.deliver(customer, notice);
        } catch (RuntimeException e) {
            log.warn("{} delivery failed again for customer {}", channel.name(), customer.id(), e);
            return new Model.Delivery(channel.name(), Model.Status.FAILED, null, null);
        }
    }
}
