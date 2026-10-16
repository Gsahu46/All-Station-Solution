package com.tijori.notifications;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
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
        return new Notification(ids.incrementAndGet(), customer.id(), notice.type(), deliveries);
    }
}
