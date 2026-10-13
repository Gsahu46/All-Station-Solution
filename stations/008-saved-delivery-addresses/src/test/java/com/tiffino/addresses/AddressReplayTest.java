package com.tiffino.addresses;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.aMapWithSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Idempotency: sending the same request again (a retry after a lost reply) leaves the same state as sending it once.
 * The status may differ (201 then 200 for PUT); the state may not.
 */
class AddressReplayTest extends ApiTest {

    private String state(long customer) throws Exception {
        return mvc.perform(get("/customers/{c}/addresses", customer)).andReturn().getResponse().getContentAsString();
    }

    @Test
    void theSamePutThreeTimesLeavesOneIdenticalAddress() throws Exception {
        String first = putAddress(42, "home", HOME).andExpect(status().isCreated()).andReturn().getResponse().getContentAsString();
        String afterOnce = state(42);
        String second = putAddress(42, "home", HOME).andExpect(status().isOk()).andReturn().getResponse().getContentAsString();
        putAddress(42, "home", HOME).andExpect(status().isOk());
        assertThat(second).isEqualTo(first);
        assertThat(state(42)).isEqualTo(afterOnce);
        mvc.perform(get("/customers/42/addresses")).andExpect(jsonPath("$", aMapWithSize(1)));
    }

    @Test
    void theSamePatchTwiceLeavesTheSameAddress() throws Exception {
        putAddress(42, "home", HOME);
        patchAddress(42, "home", "{\"landmark\":\"Gate 2\",\"line2\":null}").andExpect(status().isOk());
        String afterOnce = state(42);
        patchAddress(42, "home", "{\"landmark\":\"Gate 2\",\"line2\":null}").andExpect(status().isOk());
        assertThat(state(42)).isEqualTo(afterOnce);
    }

    @Test
    void deletingTwiceIs204BothTimes() throws Exception {
        putAddress(42, "work", HOME);
        deleteAddress(42, "work").andExpect(status().isNoContent());
        deleteAddress(42, "work").andExpect(status().isNoContent()); // the retry gets the same answer: no error screen
        mvc.perform(get("/customers/42/addresses")).andExpect(jsonPath("$", aMapWithSize(0)));
    }

    @Test
    void retriesOfDifferentLabelsDoNotTouchEachOther() throws Exception {
        putAddress(42, "home", HOME);
        putAddress(42, "work", HOME.replace("Flat 402", "Floor 3"));
        putAddress(42, "home", HOME);
        mvc.perform(get("/customers/42/addresses"))
                .andExpect(jsonPath("$", aMapWithSize(2)))
                .andExpect(jsonPath("$.work.line1").value("Floor 3, Lotus Residency"));
    }
}
