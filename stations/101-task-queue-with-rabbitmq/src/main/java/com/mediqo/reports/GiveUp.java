package com.mediqo.reports;

import org.springframework.amqp.core.Message;
import org.springframework.amqp.rabbit.retry.MessageRecoverer;
import org.springframework.amqp.rabbit.retry.RejectAndDontRequeueRecoverer;
import org.springframework.stereotype.Component;
import tools.jackson.databind.json.JsonMapper;

import java.io.IOException;
import java.io.UncheckedIOException;

/**
 * After the last retry: record why on the report, then reject the message without requeueing, so the broker moves
 * it to the dead-letter queue. It stays there for a person to look at or send back.
 */
@Component
class GiveUp implements MessageRecoverer {

    private static final JsonMapper JSON = JsonMapper.builder().build();
    private final LabReports reports;
    private final MessageRecoverer reject = new RejectAndDontRequeueRecoverer();

    GiveUp(LabReports reports) {
        this.reports = reports;
    }

    @Override
    public void recover(Message message, Throwable cause) {
        String id = JSON.readTree(message.getBody()).path("reportId").asString();
        if (reports.pages(id).isPresent()) {
            try {
                reports.saveFailure(id, rootMessage(cause));
            } catch (IOException e) {
                throw new UncheckedIOException(e);
            }
        }
        reject.recover(message, cause);
    }

    private static String rootMessage(Throwable t) {
        while (t.getCause() != null) {
            t = t.getCause();
        }
        return t.getMessage();
    }
}
