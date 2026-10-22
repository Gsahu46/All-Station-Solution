package com.dakroute.rates;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletResponse;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.node.ObjectNode;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.skyscreamer.jsonassert.JSONAssert.assertEquals;

/**
 * The docs are tested against the API, so they cannot drift: every example is sent, every documented answer is
 * compared with the real one, every field the docs call required is refused when missing, and any change to the
 * description shows as a diff against the approved copy, for review.
 */
class OpenApiDocsTest extends ApiTest {

    JsonNode operation() throws Exception {
        return spec().at("/paths/~1rate-quotes/post");
    }

    /** The status whose documented example has the same name as a request example; 200 if none does. */
    static int documentedStatus(JsonNode op, String example) {
        for (Map.Entry<String, JsonNode> r : op.get("responses").properties()) {
            for (JsonNode content : r.getValue().path("content")) {
                if (content.path("examples").has(example)) {
                    return Integer.parseInt(r.getKey());
                }
            }
        }
        return 200;
    }

    @Test
    void everyRequestExampleGetsTheStatusTheDocsGiveIt() throws Exception {
        JsonNode op = operation();
        JsonNode examples = op.at("/requestBody/content/application~1json/examples");
        assertThat(examples.propertyNames()).hasSizeGreaterThanOrEqualTo(4);
        for (Map.Entry<String, JsonNode> ex : examples.properties()) {
            MockHttpServletResponse real = quoteResponse(ex.getValue().get("value").toString());
            assertThat(real.getStatus()).as(ex.getKey()).isEqualTo(documentedStatus(op, ex.getKey()));
        }
    }

    @Test
    void everyDocumentedAnswerMatchesTheRealOne() throws Exception {
        JsonNode op = operation();
        JsonNode requests = op.at("/requestBody/content/application~1json/examples");
        for (Map.Entry<String, JsonNode> r : op.get("responses").properties()) {
            for (JsonNode content : r.getValue().path("content")) {
                for (Map.Entry<String, JsonNode> ex : content.path("examples").properties()) {
                    MockHttpServletResponse real = quoteResponse(requests.get(ex.getKey()).get("value").toString());
                    JsonNode documented = ((ObjectNode) ex.getValue().get("value").deepCopy()).remove(List.of("quoteId"));
                    assertEquals(documented.toString(), real.getContentAsString(), false);   // every documented field, with its value
                }
            }
        }
    }

    @Test
    void theFieldsTheDocsCallRequiredAreExactlyTheOnesTheApiRefusesWithout() throws Exception {
        JsonNode schema = spec().at("/components/schemas/QuoteRequest");
        List<String> required = new ArrayList<>();
        schema.get("required").forEach(n -> required.add(n.asString()));
        ObjectNode parcel = (ObjectNode) JSON.readTree(RateQuoteController.PARCEL);
        for (String field : schema.get("properties").propertyNames()) {
            ObjectNode without = parcel.deepCopy();
            without.remove(field);
            int status = quoteResponse(without.toString()).getStatus();
            assertThat(status == 400).as(field + " missing gave " + status + "; docs say required: " + required.contains(field)).isEqualTo(required.contains(field));
        }
    }

    @Test
    void theDescriptionMatchesTheApprovedCopy() throws Exception {
        String generated = JSON.writerWithDefaultPrettyPrinter().writeValueAsString(spec());
        Path approved = Path.of("src/test/resources/openapi/approved.json");
        if (!Files.exists(approved) || !JSON.readTree(Files.readString(approved)).equals(JSON.readTree(generated))) {
            Files.createDirectories(Path.of("target"));
            Files.writeString(Path.of("target/openapi-generated.json"), generated);   // review the diff, then copy it over approved.json
        }
        assertThat(JSON.readTree(Files.readString(approved))).isEqualTo(JSON.readTree(generated));
    }
}
