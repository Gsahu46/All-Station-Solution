package com.taskloom.support;

import com.fasterxml.jackson.annotation.JsonProperty;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;

import java.net.http.HttpClient;
import java.net.http.HttpTimeoutException;
import java.time.Duration;
import java.util.List;
import java.util.Map;

/**
 * Calls a model in the shape of Anthropic's Messages API (POST /v1/messages). Never retried here: every call costs money,
 * and the agent can ask again.
 */
@Component
class ModelClient {

    record Answer(String text, int inputTokens, int outputTokens, String stopReason) {
    }

    /** The provider is overloaded or down: try later. */
    static final class Busy extends RuntimeException {
        Busy(String message) {
            super(message);
        }
    }

    /** The provider refused our request (a bad request, a wrong key): a bug or a configuration error on our side. */
    static final class Refused extends RuntimeException {
        Refused(String message) {
            super(message);
        }
    }

    /** No answer within the read timeout. */
    static final class TimedOut extends RuntimeException {
        TimedOut(Throwable cause) {
            super(cause);
        }
    }

    record Content(String type, String text) {
    }

    record Usage(@JsonProperty("input_tokens") int inputTokens, @JsonProperty("output_tokens") int outputTokens) {
    }

    record Response(List<Content> content, Usage usage, @JsonProperty("stop_reason") String stopReason) {
    }

    private final RestClient http;
    private final String model;
    private final int maxOutputTokens;

    ModelClient(@Value("${taskloom.model.url}") String url, @Value("${taskloom.model.api-key}") String apiKey,
                @Value("${taskloom.model.name}") String model, @Value("${taskloom.model.max-output-tokens}") int maxOutputTokens,
                @Value("${taskloom.model.connect-timeout}") Duration connectTimeout, @Value("${taskloom.model.timeout}") Duration timeout) {
        JdkClientHttpRequestFactory factory = new JdkClientHttpRequestFactory(HttpClient.newBuilder().connectTimeout(connectTimeout).build());
        factory.setReadTimeout(timeout);
        this.http = RestClient.builder().baseUrl(url).requestFactory(factory)
                .defaultHeader("x-api-key", apiKey).defaultHeader("anthropic-version", "2023-06-01").build();
        this.model = model;
        this.maxOutputTokens = maxOutputTokens;
    }

    Answer summarise(Prompt prompt) {
        Map<String, Object> body = Map.of("model", model, "max_tokens", maxOutputTokens, "system", prompt.system(),
                "messages", List.of(Map.of("role", "user", "content", prompt.user())));
        try {
            Response r = http.post().body(body).retrieve()
                    .onStatus(ModelClient::isBusy, (req, res) -> {
                        throw new Busy("The model provider answered " + res.getStatusCode().value());
                    })
                    .body(Response.class);
            String text = r.content().stream().filter(c -> "text".equals(c.type())).map(Content::text).findFirst().orElse("");
            return new Answer(text, r.usage().inputTokens(), r.usage().outputTokens(), r.stopReason());
        } catch (HttpClientErrorException e) {
            // 400, 401, 403...: our request or our key is wrong. Asking again will not help.
            throw new Refused("The model provider refused the request: " + e.getStatusCode().value());
        } catch (ResourceAccessException e) {
            for (Throwable t = e; t != null; t = t.getCause()) {
                if (t instanceof HttpTimeoutException) {
                    throw new TimedOut(e);
                }
            }
            throw new Busy("The model provider could not be reached");
        }
    }

    private static boolean isBusy(HttpStatusCode status) {
        return status.value() == 429 || status.value() == 529 || status.is5xxServerError();
    }
}
