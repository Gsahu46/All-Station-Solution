package com.dakroute.rates;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Written first. Partners integrated from a PDF written by hand two releases ago. Its example request, copied below,
 * uses field names and units the API stopped accepting: every partner who copied it got a 400 and opened a ticket.
 */
class HandWrittenDocsTrapTest extends ApiTest {

    /** Page 4 of "Dakroute Rate API v2.pdf". */
    static final String FROM_THE_PDF = """
            {"origin": "560001", "destination": "110001", "weight_kg": 1.2, "dimensions": "30x20x10", "type": "surface"}""";

    @Test
    void thePdfsExampleIsRefusedByTheRealApi() throws Exception {
        assertThat(quoteResponse(FROM_THE_PDF).getStatus()).isEqualTo(400);
    }

    @Test
    void theGeneratedDocsDescribeTheFieldsTheApiReallyTakes() throws Exception {
        var properties = spec().at("/components/schemas/QuoteRequest/properties");
        assertThat(properties.propertyNames()).containsExactly("fromPincode", "toPincode", "weightGrams", "lengthCm", "widthCm", "heightCm", "service");
        assertThat(properties.has("weight_kg")).isFalse();
        assertThat(properties.at("/fromPincode/pattern").asString()).isEqualTo("[1-9][0-9]{5}");
        assertThat(properties.at("/lengthCm/maximum").asInt()).isEqualTo(150);
    }
}
