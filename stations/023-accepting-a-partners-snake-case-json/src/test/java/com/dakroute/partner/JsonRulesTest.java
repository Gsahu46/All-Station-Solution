package com.dakroute.partner;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import tools.jackson.databind.exc.UnrecognizedPropertyException;
import tools.jackson.databind.json.JsonMapper;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The app's own mapper: strict for our types, tolerant only where a class opts out. */
@SpringBootTest
class JsonRulesTest {

    @Autowired
    JsonMapper mapper;

    @Test
    void ourOwnTypesStillRejectUnknownFields() {
        assertThatThrownBy(() -> mapper.readValue("{\"awbNumber\":\"X\",\"surprise\":1}", TrackingEvent.class))
                .isInstanceOf(UnrecognizedPropertyException.class);
    }

    @Test
    void onlyThePartnerTypesOptOut() {
        PartnerUpdate u = mapper.readValue(ApiTest.PARTNER_PAYLOAD, PartnerUpdate.class);
        assertThat(u.awbNumber()).isEqualTo("DKR100000001IN");
        assertThat(u.location().cityName()).isEqualTo("Pune");   // hub_id inside location ignored too
    }
}
