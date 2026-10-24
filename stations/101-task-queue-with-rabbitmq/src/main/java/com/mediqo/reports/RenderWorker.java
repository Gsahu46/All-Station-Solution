package com.mediqo.reports;

import com.rabbitmq.client.Channel;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Takes render requests off the queue. The message is acknowledged only when this method returns: if the worker dies
 * half way, the broker gives the message to another worker. So a message can arrive twice, and a report that is
 * already rendered is skipped.
 */
@Component
class RenderWorker {

    record RenderRequest(String reportId) {
    }

    private static final Logger log = LoggerFactory.getLogger(RenderWorker.class);
    private final LabReports reports;
    private final long msPerPage;
    private final Map<String, AtomicInteger> rendered = new ConcurrentHashMap<>();   // for the tests and the logs
    private final Set<String> busyOnce = ConcurrentHashMap.newKeySet();

    RenderWorker(LabReports reports, @Value("${mediqo.reports.ms-per-page}") long msPerPage) {
        this.reports = reports;
        this.msPerPage = msPerPage;
    }

    @RabbitListener(queues = ReportsApplication.QUEUE)
    void render(RenderRequest request, Channel channel) throws IOException, InterruptedException {
        String id = request.reportId();
        int pages = reports.pages(id).orElseThrow(() -> new IllegalArgumentException("Unknown report " + id));
        if (Files.exists(reports.pdf(id))) {
            log.info("{} is already rendered: a repeated message, acknowledged and skipped", id);
            return;
        }
        // Simulated lab troubles: LR-0013's scan is damaged (fails every time); LR-0042's lab system is busy once.
        if (id.equals("LR-0013")) {
            throw new IllegalStateException("The scan of LR-0013 is damaged.");
        }
        if (id.equals("LR-0042") && busyOnce.add(id)) {
            throw new IllegalStateException("The lab system did not answer.");
        }
        List<String> lines = new ArrayList<>();
        for (int page = 1; page <= pages; page++) {
            if (!channel.isOpen()) {
                // Cut off from the broker: it has already put the message back for another worker. Stop, do not race it.
                log.warn("Lost the broker while rendering {}; another worker will take it", id);
                return;
            }
            Thread.sleep(msPerPage);   // simulated: laying out one page
            lines.add("Lab report " + id + " - page " + page + " of " + pages);
        }
        reports.savePdf(id, Pdf.of(lines));
        rendered.computeIfAbsent(id, k -> new AtomicInteger()).incrementAndGet();
    }

    int timesRendered(String id) {
        AtomicInteger n = rendered.get(id);
        return n == null ? 0 : n.get();
    }
}
