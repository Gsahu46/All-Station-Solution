package com.chaupal.previews;

import org.junit.jupiter.api.Test;

import java.io.InputStream;
import java.net.InetAddress;
import java.net.URI;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Written first. The old preview fetched any URL it was sent. An attacker sent the cloud metadata address and read the
 * instance's keys in the "preview". A later fix checked the name's address first, then fetched: a name that answers
 * a public address once and an internal one the next time (DNS rebinding) walked straight through.
 */
class FetchAnyUrlTrapTest extends ApiTest {

    @Test
    void theOldWayReadTheInternalSecret() throws Exception {
        try (InputStream in = URI.create(TestSites.url("127.0.0.1", "/latest/meta-data/iam/security-credentials/")).toURL().openStream()) {
            assertThat(new String(in.readAllBytes())).isEqualTo(TestSites.SECRET);
        }
    }

    @Test
    void checkingFirstAndFetchingLaterWasFooledByRebinding() throws Exception {
        AddressPolicy policy = new AddressPolicy(java.util.List.of("127.0.0.2"));
        InetAddress checked = TestSites.lookup("rebind.example")[0];
        assertThat(policy.isBlocked(checked)).isFalse();                    // "it is public, go ahead"
        InetAddress connectedTo = TestSites.lookup("rebind.example")[0];    // the fetch resolves the name again
        try (InputStream in = URI.create(TestSites.url(connectedTo.getHostAddress(), "/")).toURL().openStream()) {
            assertThat(new String(in.readAllBytes())).isEqualTo(TestSites.SECRET);
        }
    }

    @Test
    void theApiRefusesInternalAddressesAndIsNotFooledByRebinding() throws Exception {
        preview(TestSites.url("metadata.internal", "/latest/meta-data/iam/security-credentials/")).andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.detail").value("This address cannot be previewed"));
        TestSites.rebindLookups.set(0);
        preview(TestSites.url("rebind.example", "/article")).andExpect(status().isCreated())
                .andExpect(jsonPath("$.title").value("Monsoon reaches Kerala early"));   // checked and fetched from the same, public address
        assertThat(TestSites.rebindLookups.get()).isOne();                                // one lookup: no second answer to trust
    }
}
