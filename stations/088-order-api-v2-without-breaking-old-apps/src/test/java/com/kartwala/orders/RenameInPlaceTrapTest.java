package com.kartwala.orders;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.web.servlet.MockMvc;
import tools.jackson.databind.DeserializationFeature;
import tools.jackson.databind.exc.MismatchedInputException;
import tools.jackson.databind.exc.UnrecognizedPropertyException;
import tools.jackson.databind.json.JsonMapper;

import java.math.BigDecimal;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

/**
 * Written first. The old release renamed customerName to customer.name in place. Apps up to 5.x read orders with
 * the model below: reading the new shape failed and the order screen crashed for 30% of users. These tests read today's
 * answers the way that app does.
 */
@SpringBootTest
@AutoConfigureMockMvc
class RenameInPlaceTrapTest {

    /** What app 5.x reads, written like its own model class. It knows nothing of fields added later. */
    @JsonIgnoreProperties(ignoreUnknown = true)
    record OldAppOrder(long id, String customerName, BigDecimal total, String status, List<OldAppItem> items) {
    }

    record OldAppItem(String sku, int qty, BigDecimal price) {
    }

    /** The same model without ignoreUnknown, for a mapper that fails on unknown fields. */
    record StrictOldAppOrder(long id, String customerName, BigDecimal total, String status, List<OldAppItem> items) {
    }

    @Autowired
    MockMvc mvc;

    final JsonMapper json = JsonMapper.builder().build();

    String body(String path) throws Exception {
        return mvc.perform(get(path)).andReturn().getResponse().getContentAsString();
    }

    @Test
    void theRenamedShapeIsWhatBrokeTheOldApp() throws Exception {
        String renamed = body("/v2/orders/1001");   // the new shape, as if served where v1 was
        // Jackson 3 refuses a missing int (qty was renamed to quantity): the old app's screen crashes.
        assertThatThrownBy(() -> json.readValue(renamed, OldAppOrder.class)).isInstanceOf(MismatchedInputException.class)
                .hasMessageContaining("Cannot map `null` into type `int`");
        // Even a reader that lets that pass shows an order with no customer and no total.
        OldAppOrder seen = JsonMapper.builder().disable(DeserializationFeature.FAIL_ON_NULL_FOR_PRIMITIVES).build().readValue(renamed, OldAppOrder.class);
        assertThat(seen.customerName()).isNull();
        assertThat(seen.total()).isNull();
    }

    @Test
    void theOldAppStillReadsV1Completely() throws Exception {
        OldAppOrder seen = json.readValue(body("/v1/orders/1001"), OldAppOrder.class);
        assertThat(seen).isEqualTo(new OldAppOrder(1001, "Meera Iyer", new BigDecimal("1299.50"), "SHIPPED",
                List.of(new OldAppItem("KW-TEE-01", 2, new BigDecimal("499.75")), new OldAppItem("KW-CAP-07", 1, new BigDecimal("300.00")))));
    }

    @Test
    void anAddedFieldIsCompatibleOnlyForATolerantReader() throws Exception {
        String v1 = body("/v1/orders/1001");   // trackingUrl was added to v1 after app 5.x shipped
        JsonMapper strict = JsonMapper.builder().enable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES).build();
        assertThatThrownBy(() -> strict.readValue(v1, StrictOldAppOrder.class)).isInstanceOf(UnrecognizedPropertyException.class);
        assertThat(json.readValue(v1, OldAppOrder.class).customerName()).isEqualTo("Meera Iyer");
    }
}
