package com.chhotu.links;

import org.junit.jupiter.api.Test;
import org.springframework.test.context.bean.override.mockito.MockitoBean;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;
import static org.mockito.Mockito.when;

/** The first test written for this station: two campaigns, one code. The generator is forced to repeat itself. */
class OverwritingCodesTrapTest extends ApiTest {

    @MockitoBean
    CodeGenerator codes;

    @Test
    void theOldSaveLetTheSecondCampaignTakeOverTheFirstOnesLink() {
        OldLinkStore.createTable(jdbc);
        OldLinkStore.save(jdbc, "k9Qz", "https://shop.example/diwali-sale?utm_campaign=diwali");
        OldLinkStore.save(jdbc, "k9Qz", "https://shop.example/new-phones?utm_campaign=launch");   // same random code
        // Every SMS already sent for the Diwali sale now opens the phone launch.
        assertThat(OldLinkStore.target(jdbc, "k9Qz")).endsWith("utm_campaign=launch");
    }

    @Test
    void fourCharactersMadeARepeatLikelyWithinAFewThousandLinks() {
        assertThat(OldLinkStore.chanceOfARepeat(5_000, Math.pow(62, 4))).isCloseTo(0.57, within(0.01));
        assertThat(OldLinkStore.chanceOfARepeat(100_000, Math.pow(62, 7))).isLessThan(0.002);   // rare, still not never
    }

    @Test
    void nowACollisionIsRetriedAndTheFirstLinkIsUntouched() {
        when(codes.next()).thenReturn("Diwali1", "Diwali1", "Launch2");
        String first = links.create("https://shop.example/diwali-sale").orElseThrow();
        String second = links.create("https://shop.example/new-phones").orElseThrow();
        assertThat(first).isEqualTo("Diwali1");
        assertThat(second).isEqualTo("Launch2");
        assertThat(targetOf("Diwali1")).isEqualTo("https://shop.example/diwali-sale");
    }
}
