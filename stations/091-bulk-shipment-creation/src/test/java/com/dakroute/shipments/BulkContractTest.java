package com.dakroute.shipments;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class BulkContractTest extends ApiTest {

    @Test
    void aGoodBatchIsCreatedWithOneResultPerItemInOrder() throws Exception {
        bulk(List.of(item("ord-1"), item("ORD-2"))).andExpect(status().isOk()).andExpect(content().json("""
                {"created":2,"failed":0,"results":[
                  {"index":0,"ref":"ORD-1","status":"created","shipmentId":1},
                  {"index":1,"ref":"ORD-2","status":"created","shipmentId":2}]}""", true));
    }

    @Test
    void everyProblemInAnItemIsListedByField() throws Exception {
        String bad = item("ORD-1").replace("\"weightGrams\":1200", "\"weightGrams\":0").replace("9810000001", "12345").replace("\"Meera Iyer\"", "\"  \"");
        bulk(List.of(bad)).andExpect(jsonPath("$.created").value(0)).andExpect(content().json("""
                {"results":[{"index":0,"status":"failed","errors":[
                  {"field":"to.name","message":"must not be blank"},
                  {"field":"to.phone","message":"must be a 10-digit Indian mobile number"},
                  {"field":"weightGrams","message":"must be greater than or equal to 1"}]}]}"""));
    }

    @Test
    void aRefUsedBeforeOrTwiceInTheBatchFailsThatItemOnly() throws Exception {
        bulk(List.of(item("ORD-1")));
        bulk(List.of(item("ORD-1").replace("1200", "1500"), item("ORD-2"), item("ord-2").replace("1200", "900"))).andExpect(jsonPath("$.created").value(1))
                .andExpect(jsonPath("$.results[0].errors[0].message").value("is already used by another shipment"))
                .andExpect(jsonPath("$.results[1].status").value("created"))
                .andExpect(jsonPath("$.results[2].errors[0].field").value("ref"));
        assertThat(count()).isEqualTo(2);
    }

    @Test
    void theBatchAsAWholeMustBeUsable() throws Exception {
        bulkBody("{\"shipments\":[]}").andExpect(status().isBadRequest());
        bulkBody("{}").andExpect(status().isBadRequest());
        bulkBody("{\"shipments\":[" + item("ORD-1").replace("1200", "\"heavy\"") + "]}").andExpect(status().isBadRequest());   // not JSON of the right shape: nothing to report per item
        bulkBody("{\"shipments\":[null]}").andExpect(status().isOk()).andExpect(jsonPath("$.results[0].errors[0].message").value("must not be null"));
        assertThat(count()).isZero();
    }

    @Test
    void fiveHundredIsTheLimit() throws Exception {
        List<String> items = new ArrayList<>();
        for (int i = 0; i < 500; i++) {
            items.add(item("ORD-" + i));
        }
        bulk(items).andExpect(status().isOk()).andExpect(jsonPath("$.created").value(500));
        jdbc.sql("TRUNCATE shipments RESTART IDENTITY").update();
        items.add(item("ORD-500"));
        bulk(items).andExpect(status().isBadRequest());
        assertThat(count()).isZero();
    }
}
