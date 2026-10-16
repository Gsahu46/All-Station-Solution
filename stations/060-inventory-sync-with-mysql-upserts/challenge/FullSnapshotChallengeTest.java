package com.basketo.inventory;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: PUT /warehouses/{id}/stock?mode=full says "this is everything on the shelves": every SKU of that
 * warehouse missing from the snapshot is set to 0 (kept, not deleted), and the response says how many with
 * "zeroedSkus". Without the parameter, the sync works as before. Other warehouses are never touched.
 */
class FullSnapshotChallengeTest extends ApiTest {

    @Test
    void aFullSnapshotZeroesWhatIsMissing() throws Exception {
        sync(1, items(5, 9)).andExpect(status().isOk());
        sync(2, items(5, 9)).andExpect(status().isOk());
        mvc.perform(put("/warehouses/1/stock").param("mode", "full").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"items\":[{\"sku\":\"SKU-00001\",\"quantity\":4},{\"sku\":\"SKU-00002\",\"quantity\":6}]}"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.zeroedSkus").value(3)).andExpect(jsonPath("$.skusInWarehouse").value(5));
        assertThat(quantity(1, "SKU-00001")).isEqualTo(4);
        assertThat(quantity(1, "SKU-00005")).isZero();
        assertThat(quantity(2, "SKU-00005")).isEqualTo(9);
    }

    @Test
    void withoutTheModeMissingSkusAreLeftAlone() throws Exception {
        sync(1, items(5, 9)).andExpect(status().isOk());
        sync(1, "[{\"sku\":\"SKU-00001\",\"quantity\":4}]").andExpect(status().isOk()).andExpect(jsonPath("$.zeroedSkus").value(0));
        assertThat(quantity(1, "SKU-00005")).isEqualTo(9);
    }
}
