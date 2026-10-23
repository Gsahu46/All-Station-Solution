package com.mapwise.geocode;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class ApiKeySecurityTest extends ApiTest {

    @Test
    void withoutAValidKeyInTheHeaderIt401s() throws Exception {
        geocode(null, "MG Road, Bengaluru").andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.detail").value("Send your API key in the X-Api-Key header."));
        geocode("mw_demo_zoomkart_wrong", "MG Road, Bengaluru").andExpect(status().isUnauthorized());
        geocode(ZOOMKART.toUpperCase(java.util.Locale.ROOT), "MG Road, Bengaluru").andExpect(status().isUnauthorized());   // keys are exact
        geocode("k".repeat(10_000), "MG Road, Bengaluru").andExpect(status().isUnauthorized());
        // A real key in the URL is refused, so partners stop putting it where logs keep it.
        mvc.perform(get("/geocode").param("address", "MG Road, Bengaluru").param("api_key", ZOOMKART)).andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.detail").value("Send the key in the X-Api-Key header, not in the URL."));
        mvc.perform(get("/partners/1/usage").header("X-Api-Key", ZOOMKART)).andExpect(jsonPath("$.usedToday").value(1));   // none of those counted
    }

    @Test
    void aSuspendedKeyIs403() throws Exception {
        geocode(OLD_MAPS, "MG Road, Bengaluru").andExpect(status().isForbidden())
                .andExpect(jsonPath("$.detail").value("This API key is suspended. Contact Mapwise."));
    }

    @Test
    void aPartnerCannotReadAnotherPartnersUsage() throws Exception {
        mvc.perform(get("/partners/2/usage").header("X-Api-Key", ZOOMKART)).andExpect(status().isForbidden());
        mvc.perform(get("/partners/1/usage").header("X-Api-Key", ZOOMKART)).andExpect(status().isOk()).andExpect(jsonPath("$.partnerId").value(1));
        mvc.perform(get("/partners/x/usage").header("X-Api-Key", ZOOMKART)).andExpect(status().isBadRequest());
    }

    @Test
    void maliciousAddressesAreRefusedOrHarmless() throws Exception {
        for (String address : new String[]{"MG Road\r\nX-Injected: 1", "MG Road\u0000", "MG\tRoad", "x".repeat(5000)}) {
            geocode(ZOOMKART, address).andExpect(status().isBadRequest());
        }
        for (String address : new String[]{"' OR 1=1 --", "../../etc/passwd", "${jndi:ldap://example.invalid/a}"}) {
            geocode(ZOOMKART, address).andExpect(status().isNotFound());   // just text that is not a place
        }
        assertThat(answer(ZOOMKART)).isEqualTo(200);
    }
}
