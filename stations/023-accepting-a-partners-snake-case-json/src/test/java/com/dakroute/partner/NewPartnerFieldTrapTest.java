package com.dakroute.partner;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.DeserializationFeature;
import tools.jackson.databind.PropertyNamingStrategies;
import tools.jackson.databind.annotation.JsonNaming;
import tools.jackson.databind.exc.UnrecognizedPropertyException;
import tools.jackson.databind.json.JsonMapper;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The first test written for this station: it reproduces the two ways the old code broke on partner JSON. */
class NewPartnerFieldTrapTest extends ApiTest {

    /** The "before" DTO: snake_case mapped, but strict like the rest of the platform. Kept only in tests. */
    @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
    record OldStrictUpdate(String awbNumber, String statusCode, String eventTime, Object location, String promisedBy) {
    }

    /** The other "before" DTO: camelCase names, lenient. Kept only in tests. */
    record OldCamelUpdate(String awbNumber, String statusCode, String eventTime) {
    }

    static final JsonMapper STRICT = JsonMapper.builder().enable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES).build();
    static final JsonMapper LENIENT = JsonMapper.builder().build();   // Jackson 3's own default: unknown fields ignored

    @Test
    void aStrictMapperRejectsThePayloadTheDayThePartnerAddsAField() {
        assertThatThrownBy(() -> STRICT.readValue(PARTNER_PAYLOAD, OldStrictUpdate.class))
                .isInstanceOf(UnrecognizedPropertyException.class)
                .hasMessageContaining("rider_phone");
    }

    @Test
    void camelCaseNamesReadNothingAndSayNothing() {
        OldCamelUpdate u = LENIENT.readValue(PARTNER_PAYLOAD, OldCamelUpdate.class);
        assertThat(u.awbNumber()).isNull();     // "awb_number" never matched "awbNumber"
        assertThat(u.statusCode()).isNull();
        assertThat(u.eventTime()).isNull();
    }

    @Test
    void theRealEndpointAcceptsThePayloadWithItsNewFields() throws Exception {
        update(PARTNER_PAYLOAD)
                .andExpect(status().isAccepted())
                .andExpect(jsonPath("$.event.awbNumber").value("DKR100000001IN"))
                .andExpect(jsonPath("$.event.status").value("OUT_FOR_DELIVERY"));
    }
}
