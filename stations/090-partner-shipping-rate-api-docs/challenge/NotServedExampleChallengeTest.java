package com.dakroute.rates;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Challenge 1: document the second 422. Add a request example named "not-served" (a parcel to PIN 744101) and a 422
 * example with the same name. OpenApiDocsTest then sends it and compares the answer; approve the new description.
 */
class NotServedExampleChallengeTest extends ApiTest {

    @Test
    void theNotServedAnswerIsDocumentedWithAnExample() throws Exception {
        JsonNode op = spec().at("/paths/~1rate-quotes/post");
        assertThat(op.at("/requestBody/content/application~1json/examples/not-served/value/toPincode").asString()).isEqualTo("744101");
        assertThat(op.at("/responses/422/content/application~1problem+json/examples/not-served/value/detail").asString()).isEqualTo("This PIN code is not served yet");
    }
}
