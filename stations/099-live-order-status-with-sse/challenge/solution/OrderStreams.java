package com.tiffino.orders;

import com.fasterxml.jackson.annotation.JsonInclude;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayDeque;
import java.util.Deque;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.stream.Collectors;
import java.util.stream.LongStream;

/**
 * Each order's status, its recent events, and the streams listening to it. Every stream has a timeout and is
 * removed when it completes, times out or fails, so a client that leaves costs nothing for long.
 * shortcut: in this server's memory; with several servers, publish status changes through a broker (Valkey pub/sub,
 * Kafka) so every server can tell its own subscribers.
 */
@Service
class OrderStreams {

    enum Status {
        PLACED, ACCEPTED, COOKING, OUT_FOR_DELIVERY, DELIVERED;

        Optional<Status> next() {
            return ordinal() + 1 < values().length ? Optional.of(values()[ordinal() + 1]) : Optional.empty();
        }
    }

    /** Challenge 1: a rider's position. */
    record Position(double lat, double lng) {
    }

    /** A status change, or (challenge 1) a position: numbered in one sequence, so reconnects replay both. */
    record Event(long id, long orderId, Status status, Instant at, @JsonInclude(JsonInclude.Include.NON_NULL) Position position) {
    }

    /** Challenge 2: a customer has as many open streams as allowed (tiffino.sse.max-streams-per-customer, demo default 50). */
    static final class TooManyStreams extends RuntimeException {
    }

    static final class Order {
        final long id;
        final String customer;
        Status status = Status.PLACED;
        long lastEventId;
        final Deque<Event> history = new ArrayDeque<>();
        final List<SseEmitter> streams = new CopyOnWriteArrayList<>();

        Order(long id, String customer) {
            this.id = id;
            this.customer = customer;
            history.add(new Event(++lastEventId, id, status, Instant.now(), null));
        }
    }

    /** Demo orders 1001 to 1099: odd ones are Riya's, even ones Kabir's. */
    private final Map<Long, Order> orders = LongStream.rangeClosed(1001, 1099).boxed()
            .collect(Collectors.toUnmodifiableMap(id -> id, id -> new Order(id, id % 2 == 1 ? "riya" : "kabir")));
    private final Map<String, Integer> openByCustomer = new HashMap<>();   // challenge 2, guarded by itself
    private final int maxStreamsPerCustomer;   // challenge 2
    private final Duration timeout;
    private final Duration retry;
    private final int historySize;

    OrderStreams(@Value("${tiffino.sse.timeout}") Duration timeout, @Value("${tiffino.sse.retry}") Duration retry,
                 @Value("${tiffino.sse.history}") int historySize,
                 @Value("${tiffino.sse.max-streams-per-customer:50}") int maxStreamsPerCustomer) {
        this.maxStreamsPerCustomer = maxStreamsPerCustomer;
        this.timeout = timeout;
        this.retry = retry;
        this.historySize = historySize;
    }

    Optional<Order> order(long id, String customer) {
        return Optional.ofNullable(orders.get(id)).filter(o -> o.customer.equals(customer));
    }

    Optional<Order> order(long id) {
        return Optional.ofNullable(orders.get(id));
    }

    /**
     * A stream for one order: what the client missed (or the current status), then every change. Empty when the
     * order is delivered and the client has seen that: the controller answers 204, which tells the browser to stop.
     */
    Optional<SseEmitter> subscribe(Order order, Long lastEventId) {
        synchronized (order) {   // nothing can change between the replay and joining the list
            if (order.status == Status.DELIVERED && lastEventId != null && lastEventId >= order.lastEventId) {
                return Optional.empty();
            }
            SseEmitter emitter = new SseEmitter(timeout.toMillis());
            List<Event> missed = lastEventId == null ? null
                    : order.history.stream().filter(e -> e.id() > lastEventId).toList();
            boolean gap = missed != null && !missed.isEmpty() && missed.getFirst().id() != lastEventId + 1;
            try {
                // The reconnect delay first, always: it also sends the headers at once, even when nothing was missed.
                emitter.send(SseEmitter.event().reconnectTime(retry.toMillis()));
                if (missed == null || gap) {
                    // First visit, or events we no longer keep: the current status instead of a hole in the story.
                    emitter.send(SseEmitter.event().id(Long.toString(order.lastEventId)).name("snapshot")
                            .data(order.history.getLast(), MediaType.APPLICATION_JSON));
                } else {
                    for (Event e : missed) {
                        emitter.send(event(e));
                    }
                }
            } catch (IOException e) {
                emitter.completeWithError(e);
                return Optional.of(emitter);
            }
            if (order.status == Status.DELIVERED) {
                emitter.complete();   // the story is over: no need to stay connected
                return Optional.of(emitter);
            }
            synchronized (openByCustomer) {   // challenge 2
                if (openByCustomer.getOrDefault(order.customer, 0) >= maxStreamsPerCustomer) {
                    emitter.complete();
                    throw new TooManyStreams();
                }
                openByCustomer.merge(order.customer, 1, Integer::sum);
            }
            order.streams.add(emitter);
            // However the stream ends (delivered, timed out, a failed write), it leaves the list.
            emitter.onCompletion(() -> {
                if (order.streams.remove(emitter)) {
                    synchronized (openByCustomer) {
                        openByCustomer.merge(order.customer, -1, Integer::sum);
                    }
                }
            });
            // On timeout, end it ourselves: otherwise Spring logs an AsyncRequestTimeoutException for every stream.
            // The browser reconnects with Last-Event-ID and misses nothing.
            emitter.onTimeout(emitter::complete);
            return Optional.of(emitter);
        }
    }

    /** The kitchen or the rider moves the order on, one step at a time. Empty if that is not the next step. */
    Optional<Event> advance(Order order, Status to) {
        synchronized (order) {
            if (order.status.next().filter(to::equals).isEmpty()) {
                return Optional.empty();
            }
            order.status = to;
            Event event = append(order, to, null);
            // shortcut: sends happen on this request's thread, one stream after another; a client that reads slowly
            // makes the kitchen wait. Hand the sends to an executor when an order has many watchers.
            for (SseEmitter stream : order.streams) {
                try {
                    stream.send(event(event));
                    if (to == Status.DELIVERED) {
                        stream.complete();
                    }
                } catch (IOException | IllegalStateException gone) {
                    drop(stream, gone);
                }
            }
            return Optional.of(event);
        }
    }

    /** Challenge 1: the rider's position, only while out for delivery. Empty otherwise. */
    Optional<Event> locate(Order order, Position position) {
        synchronized (order) {
            if (order.status != Status.OUT_FOR_DELIVERY) {
                return Optional.empty();
            }
            Event event = append(order, order.status, position);
            for (SseEmitter stream : order.streams) {
                try {
                    stream.send(event(event));
                } catch (IOException | IllegalStateException gone) {
                    drop(stream, gone);
                }
            }
            return Optional.of(event);
        }
    }

    private Event append(Order order, Status status, Position position) {
        Event event = new Event(++order.lastEventId, order.id, status, Instant.now(), position);
        order.history.add(event);
        while (order.history.size() > historySize) {
            order.history.removeFirst();
        }
        return event;
    }

    /** A comment line to every stream. A client that has gone makes the write fail; its stream is dropped, not retried. */
    @Scheduled(fixedRateString = "${tiffino.sse.heartbeat}")
    void heartbeat() {
        for (Order order : orders.values()) {
            for (SseEmitter stream : order.streams) {
                try {
                    stream.send(SseEmitter.event().comment("keep-alive"));
                } catch (IOException | IllegalStateException gone) {
                    drop(stream, gone);
                }
            }
        }
    }

    int streams() {
        return orders.values().stream().mapToInt(o -> o.streams.size()).sum();
    }

    /** Ends a stream whose client has gone; its completion callback takes it off the list. */
    private static void drop(SseEmitter stream, Exception why) {
        stream.completeWithError(why);
    }

    private static SseEmitter.SseEventBuilder event(Event e) {
        return SseEmitter.event().id(Long.toString(e.id())).name(e.position() == null ? "status" : "location").data(e, MediaType.APPLICATION_JSON);
    }
}
