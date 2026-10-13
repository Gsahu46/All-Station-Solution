package com.kartwala.wishlist;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The key on its own: the equals/hashCode contract, normalising, and use in HashSet and HashMap. */
class SkuTest {

    private final Locale original = Locale.getDefault();

    @AfterEach
    void restoreLocale() {
        Locale.setDefault(original);
    }

    @Test
    void equalSkusHaveEqualHashCodes() {
        List<Sku> same = List.of(new Sku("ph-12"), new Sku("PH-12"), new Sku(" PH-12 "), new Sku("Ph-12\t"));
        for (Sku a : same) {
            for (Sku b : same) {
                assertThat(a).isEqualTo(b);
                assertThat(a.hashCode()).isEqualTo(b.hashCode()); // the half of the contract the trap forgot
            }
        }
        assertThat(new Sku("PH-12")).isNotEqualTo(new Sku("PH-13")).isNotEqualTo(null).isNotEqualTo("PH-12");
    }

    @Test
    void aHashSetAndAHashMapTreatThemAsOneKey() {
        Set<Sku> set = new HashSet<>(List.of(new Sku("ph-12"), new Sku("PH-12"), new Sku(" PH-12 ")));
        assertThat(set).containsExactly(new Sku("PH-12"));
        Map<Sku, Integer> wishes = new HashMap<>();
        for (String raw : List.of("ph-12", "PH-12", "tv-55")) {
            wishes.merge(new Sku(raw), 1, Integer::sum);
        }
        assertThat(wishes).containsEntry(new Sku("PH-12"), 2).containsEntry(new Sku("TV-55"), 1);
    }

    @Test
    void aTurkishServerLocaleDoesNotChangeTheKey() {
        Locale.setDefault(Locale.forLanguageTag("tr-TR")); // "mi-11x".toUpperCase() would be "Mİ-11X"
        assertThat(new Sku("mi-11x")).isEqualTo(new Sku("MI-11X"));
    }

    @Test
    void malformedValuesAreRefused() {
        for (String bad : new String[]{"", "   ", "P", "-PH", "PH 12", "PH_12", "A".repeat(31)}) {
            assertThatThrownBy(() -> new Sku(bad)).as(bad).isInstanceOf(IllegalArgumentException.class);
        }
        assertThatThrownBy(() -> new Sku(null)).isInstanceOf(IllegalArgumentException.class);
    }
}
