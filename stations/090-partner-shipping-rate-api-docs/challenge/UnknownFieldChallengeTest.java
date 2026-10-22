package com.dakroute.rates;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: partners still sending the old PDF's fields get told which field is wrong: unknown fields are refused
 * (400) by name, and a missing or mistyped field is named too, with where the docs are. The docs show the old PDF's
 * body as a request example "from-the-old-pdf". Jackson 3 reports a record's missing number before an unknown field.
 */
class UnknownFieldChallengeTest extends ApiTest {

    @Test
    void theWrongFieldIsNamed() throws Exception {
        quote(HandWrittenDocsTrapTest.FROM_THE_PDF).andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.detail").value("Field 'weightGrams' is missing or has the wrong type. The fields are described at /v3/api-docs"));
        quote("{\"fromPincode\":\"560001\",\"toPincode\":\"110001\",\"weightGrams\":500,\"lengthCm\":10,\"widthCm\":10,\"heightCm\":10,\"service\":\"STANDARD\",\"cod\":true}")
                .andExpect(status().isBadRequest()).andExpect(jsonPath("$.detail").value("Unknown field 'cod'. The fields are described at /v3/api-docs"));
    }

    @Test
    void theDocsShowIt() throws Exception {
        JsonNode op = spec().at("/paths/~1rate-quotes/post");
        assertThat(op.at("/requestBody/content/application~1json/examples/from-the-old-pdf/value/origin").asString()).isEqualTo("560001");
        assertThat(op.at("/responses/400/content/application~1problem+json/examples/from-the-old-pdf/value/detail").asString()).startsWith("Field 'weightGrams' is missing");
    }
}
