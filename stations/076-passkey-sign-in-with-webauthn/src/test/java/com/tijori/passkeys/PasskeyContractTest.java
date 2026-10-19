package com.tijori.passkeys;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.matchesPattern;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class PasskeyContractTest extends ApiTest {

    @Test
    void passwordAndCodeGiveATokenThatOpensTheAccount() throws Exception {
        String token = body(codeSignIn("Zoya@Example.com", "zoya-demo-pass", currentCode()).andExpect(status().isOk())
                .andExpect(jsonPath("$.signedInWith", contains("pwd", "otp", "mfa"))).andExpect(jsonPath("$.expiresIn").value(600))).get("accessToken").asString();
        me(token).andExpect(status().isOk()).andExpect(jsonPath("$.name").value("Zoya Khan")).andExpect(jsonPath("$.balancePaise").value(4250000));
    }

    @Test
    void registrationOptionsNameThisSiteAndAskForAPasskeyWithUserVerification() throws Exception {
        JsonNode o = registrationOptions(codeToken("zoya"));
        assertThat(o.path("rp").path("id").asString()).isEqualTo("tijori.example");
        assertThat(o.path("challenge").asString()).matches("[\\w-]{43}");
        assertThat(o.path("user").path("name").asString()).isEqualTo("zoya@example.com");
        assertThat(o.path("user").path("id").asString()).matches("[\\w-]{43}").doesNotContain("zoya");
        assertThat(o.path("authenticatorSelection").path("userVerification").asString()).isEqualTo("required");
        assertThat(o.path("authenticatorSelection").path("residentKey").asString()).isEqualTo("required");
    }

    @Test
    void aRegisteredPasskeySignsInWithoutAPassword() throws Exception {
        String token = codeToken("zoya");
        Device phone = new Device();
        register(token, "Zoya's phone", phone.create(registrationOptions(token))).andExpect(status().isCreated())
                .andExpect(header().string("Location", matchesPattern("/webauthn/passkeys/[\\w-]+"))).andExpect(jsonPath("$.label").value("Zoya's phone"));
        String passkeyToken = body(authenticate(phone.get(authenticationOptions())).andExpect(status().isOk())
                .andExpect(jsonPath("$.signedInWith", contains("hwk", "user")))).get("accessToken").asString();
        me(passkeyToken).andExpect(jsonPath("$.name").value("Zoya Khan"));
    }

    @Test
    void wrongPasswordWrongCodeOrUnknownEmailAreTheSame401() throws Exception {
        codeSignIn("zoya@example.com", "not-her-password", currentCode()).andExpect(status().isUnauthorized()).andExpect(jsonPath("$.detail").value("Wrong email, password or code"));
        codeSignIn("zoya@example.com", "zoya-demo-pass", "000000".equals(currentCode()) ? "111111" : "000000").andExpect(status().isUnauthorized()).andExpect(jsonPath("$.detail").value("Wrong email, password or code"));
        codeSignIn("nobody@example.com", "any-password", currentCode()).andExpect(status().isUnauthorized()).andExpect(jsonPath("$.detail").value("Wrong email, password or code"));
    }

    @Test
    void badBodiesAre400() throws Exception {
        codeSignIn("zoya@example.com", "zoya-demo-pass", "12345").andExpect(status().isBadRequest());
        codeSignIn("not-an-email", "zoya-demo-pass", "123456").andExpect(status().isBadRequest());
        String token = codeToken("zoya");
        send("/webauthn/registration", token, "{\"label\":\"\",\"credential\":{}}").andExpect(status().isBadRequest());
        send("/webauthn/registration", token, "{\"label\":\"x\"}").andExpect(status().isBadRequest());
    }
}
