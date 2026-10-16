package com.basketo.inventory;

import org.junit.jupiter.api.Test;
import org.springframework.dao.PessimisticLockingFailureException;
import org.springframework.test.context.bean.override.mockito.MockitoSpyBean;

import java.util.Locale;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class StockContractTest extends ApiTest {

    @MockitoSpyBean
    StockSync stockSync;

    @Test
    void aSnapshotSetsTheCountsAndTheNextOneOverwritesThem() throws Exception {
        sync(1, "[{\"sku\":\"RICE-5KG\",\"quantity\":40},{\"sku\":\"ATTA-10KG\",\"quantity\":12}]").andExpect(status().isOk())
                .andExpect(jsonPath("$.warehouseId").value(1)).andExpect(jsonPath("$.syncedItems").value(2)).andExpect(jsonPath("$.skusInWarehouse").value(2));
        sync(1, "[{\"sku\":\"RICE-5KG\",\"quantity\":35}]").andExpect(status().isOk())
                .andExpect(jsonPath("$.syncedItems").value(1)).andExpect(jsonPath("$.skusInWarehouse").value(2));
        assertThat(quantity(1, "RICE-5KG")).isEqualTo(35);   // the count, not 40 + 35
        assertThat(quantity(1, "ATTA-10KG")).isEqualTo(12);  // not in this snapshot: left alone
        assertThat(rows(1)).isEqualTo(2);
    }

    @Test
    void theSameSnapshotTwiceLeavesTheSameRows() throws Exception {
        sync(2, items(3, 7)).andExpect(status().isOk());
        sync(2, items(3, 7)).andExpect(status().isOk()).andExpect(jsonPath("$.skusInWarehouse").value(3));
        assertThat(rows(2)).isEqualTo(3);
        assertThat(quantity(2, "SKU-00002")).isEqualTo(7);
    }

    @Test
    void aThousandSkusGoInTwoChunks() throws Exception {
        sync(1, items(1000, 3)).andExpect(status().isOk()).andExpect(jsonPath("$.syncedItems").value(1000));
        assertThat(rows(1)).isEqualTo(1000);
    }

    @Test
    void skusAreUpperCasedTheSameWayInEveryLocale() throws Exception {
        Locale before = Locale.getDefault();
        Locale.setDefault(Locale.forLanguageTag("tr-TR"));   // in Turkish, "i".toUpperCase() is "İ", which the SKU rule refuses
        try {
            sync(1, "[{\"sku\":\"milk-1l\",\"quantity\":9}]").andExpect(status().isOk());
        } finally {
            Locale.setDefault(before);
        }
        assertThat(quantity(1, "MILK-1L")).isEqualTo(9);
    }

    @Test
    void theSameSkuTwiceIs422EvenInDifferentCase() throws Exception {
        sync(1, "[{\"sku\":\"dal-1kg\",\"quantity\":5},{\"sku\":\"DAL-1KG\",\"quantity\":8}]").andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.detail").value("SKU DAL-1KG appears twice; which count is right?"));
        assertThat(rows(1)).isZero();
    }

    @Test
    void anUnknownWarehouseIs404() throws Exception {
        sync(99, items(2, 1)).andExpect(status().isNotFound()).andExpect(jsonPath("$.detail").value("No warehouse 99"));
    }

    @Test
    void malformedSnapshotsAre400() throws Exception {
        for (String bad : new String[]{"[]", items(1001, 1), "[{\"sku\":\"RICE-5KG\",\"quantity\":-1}]",
                "[{\"sku\":\"RICE-5KG\",\"quantity\":2.5}]", "[{\"sku\":\"RICE-5KG\"}]", "[{\"sku\":\"RICE 5KG\",\"quantity\":1}]",
                "[{\"sku\":\"RICE-5KG\",\"quantity\":1000001}]", "[null]"}) {
            sync(1, bad).andExpect(status().isBadRequest());
        }
        assertThat(rows(1)).isZero();
    }

    @Test
    void aDeadlockVictimIsRunAgain() throws Exception {
        doThrow(new PessimisticLockingFailureException("Deadlock found when trying to get lock"))
                .doCallRealMethod().when(stockSync).sync(anyLong(), anyList());
        sync(1, items(2, 4)).andExpect(status().isOk());
        verify(stockSync, times(2)).sync(anyLong(), anyList());
        assertThat(rows(1)).isEqualTo(2);
    }

    @Test
    void threeDeadlocksInARowAre503() throws Exception {
        doThrow(new PessimisticLockingFailureException("Deadlock found when trying to get lock")).when(stockSync).sync(anyLong(), anyList());
        sync(1, items(2, 4)).andExpect(status().isServiceUnavailable());
        verify(stockSync, times(3)).sync(anyLong(), anyList());
    }
}
