package com.tijori.passkeys;

import com.webauthn4j.WebAuthnManager;
import com.webauthn4j.converter.AttestedCredentialDataConverter;
import com.webauthn4j.converter.util.ObjectConverter;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.node.ObjectNode;

import java.io.ByteArrayOutputStream;
import java.security.MessageDigest;
import java.security.Signature;
import java.util.Base64;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Written first. The old passkey code checked only the signature with the stored public key: not which challenge was
 * signed, not which page asked, not which site the passkey was made for. Each test builds one answer the old code
 * accepted, then sends it to the real API.
 */
class UncheckedCeremonyTrapTest extends ApiTest {

    static final Base64.Decoder UNB64 = Base64.getUrlDecoder();

    /** The old sign-in check, as it was: is this a valid signature by the stored key? */
    boolean oldSignatureOnlyCheck(JsonNode assertion) throws Exception {
        byte[] stored = jdbc.sql("SELECT attested_credential_data FROM passkeys WHERE credential_id = ?")
                .param(UNB64.decode(assertion.path("rawId").asString())).query(byte[].class).single();
        var key = new AttestedCredentialDataConverter(new ObjectConverter()).convert(stored).getCOSEKey().getPublicKey();
        JsonNode r = assertion.path("response");
        ByteArrayOutputStream signed = new ByteArrayOutputStream();
        signed.write(UNB64.decode(r.path("authenticatorData").asString()));
        signed.write(MessageDigest.getInstance("SHA-256").digest(UNB64.decode(r.path("clientDataJSON").asString())));
        Signature verifier = Signature.getInstance("SHA256withECDSA");
        verifier.initVerify(key);
        verifier.update(signed.toByteArray());
        return verifier.verify(UNB64.decode(r.path("signature").asString()));
    }

    @Test
    void aSignInCapturedOnceAndSentAgainIsRefused() throws Exception {
        Device phone = passkeyFor("zoya");
        ObjectNode signIn = phone.get(authenticationOptions());
        authenticate(signIn).andExpect(status().isOk());
        // Captured from a log or a proxy: the very same answer, a minute later. A synced passkey's counter stays 0,
        // so only the used-up challenge stops it.
        later(java.time.Duration.ofMinutes(1));
        assertThat(oldSignatureOnlyCheck(signIn)).isTrue();             // the old code: signed in again
        authenticate(signIn).andExpect(status().isUnauthorized());      // its challenge was used up
    }

    @Test
    void aSignInAnsweredForAPhishingPageIsRefused() throws Exception {
        Device phone = passkeyFor("zoya");
        // tijori-login.example fetches a real challenge from Tijori and gets the passkey to answer it on its own page.
        ObjectNode relayed = phone.at("https://tijori-login.example").get(authenticationOptions());
        assertThat(oldSignatureOnlyCheck(relayed)).isTrue();
        authenticate(relayed).andExpect(status().isUnauthorized());     // clientDataJSON names the page that asked
    }

    @Test
    void aPasskeyMadeForAnotherSiteIsNotRegistered() throws Exception {
        String token = codeToken("zoya");
        // A look-alike page asks for a passkey for its own relying party, then hands the result to Tijori.
        ObjectNode forOtherSite = new Device().create(registrationOptions(token), "tijori-login.example");
        assertThat(WebAuthnManager.createNonStrictWebAuthnManager().parseRegistrationResponseJSON(forOtherSite.toString())).isNotNull();   // the old code stored any parsable key
        register(token, "Zoya's phone", forOtherSite).andExpect(status().isBadRequest());
        assertThat(jdbc.sql("SELECT count(*) FROM passkeys").query(Long.class).single()).isZero();
    }

    @Test
    void theRightAnswerSignsIn() throws Exception {
        // The control: same passkey, Tijori's own page, a fresh challenge.
        Device phone = passkeyFor("zoya");
        authenticate(phone.get(authenticationOptions())).andExpect(status().isOk());
    }
}
