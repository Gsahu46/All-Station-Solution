package com.tijori.passkeys;

import com.webauthn4j.data.AttestationConveyancePreference;
import com.webauthn4j.data.AuthenticatorAssertionResponse;
import com.webauthn4j.data.AuthenticatorAttestationResponse;
import com.webauthn4j.data.AuthenticatorSelectionCriteria;
import com.webauthn4j.data.PublicKeyCredential;
import com.webauthn4j.data.PublicKeyCredentialCreationOptions;
import com.webauthn4j.data.PublicKeyCredentialDescriptor;
import com.webauthn4j.data.PublicKeyCredentialParameters;
import com.webauthn4j.data.PublicKeyCredentialRequestOptions;
import com.webauthn4j.data.PublicKeyCredentialRpEntity;
import com.webauthn4j.data.PublicKeyCredentialType;
import com.webauthn4j.data.PublicKeyCredentialUserEntity;
import com.webauthn4j.data.ResidentKeyRequirement;
import com.webauthn4j.data.UserVerificationRequirement;
import com.webauthn4j.data.attestation.statement.COSEAlgorithmIdentifier;
import com.webauthn4j.data.client.Origin;
import com.webauthn4j.data.client.challenge.DefaultChallenge;
import com.webauthn4j.test.authenticator.webauthn.NoneAttestationAuthenticator;
import com.webauthn4j.test.authenticator.webauthn.WebAuthnAuthenticatorAdaptor;
import com.webauthn4j.test.client.ClientPlatform;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;
import tools.jackson.databind.node.ObjectNode;

import java.util.ArrayList;
import java.util.Base64;
import java.util.List;

/**
 * A phone: an authenticator (webauthn4j's emulator, with real keys and real signatures) and the browser in front of
 * it, at a web origin. It turns the server's options JSON into the JSON a browser would send back. By default its
 * signature counter stays 0, as synced passkeys commonly report; securityKey() counts up like a hardware key.
 */
final class Device {

    static final String TIJORI = "https://app.tijori.example";
    static final JsonMapper JSON = JsonMapper.builder().build();
    private static final Base64.Encoder B64 = Base64.getUrlEncoder().withoutPadding();
    private static final Base64.Decoder UNB64 = Base64.getUrlDecoder();

    final ClientPlatform browser;

    Device() {
        this(false);
    }

    private Device(boolean counting) {
        NoneAttestationAuthenticator authenticator = new NoneAttestationAuthenticator();
        authenticator.setCountUpEnabled(counting);
        browser = new ClientPlatform(new Origin(TIJORI), new WebAuthnAuthenticatorAdaptor(authenticator));
    }

    static Device securityKey() {
        return new Device(true);
    }

    /** The same authenticator, but the page asking is at another origin (a phishing page, or a client that lies). */
    Device at(String origin) {
        browser.setOrigin(new Origin(origin));
        return this;
    }

    /** navigator.credentials.create(options), as JSON. rpIdOverride plays a page that asks for another relying party. */
    ObjectNode create(JsonNode o, String rpIdOverride) {
        List<PublicKeyCredentialParameters> algs = new ArrayList<>();
        o.path("pubKeyCredParams").forEach(p -> algs.add(new PublicKeyCredentialParameters(PublicKeyCredentialType.PUBLIC_KEY, COSEAlgorithmIdentifier.create(p.path("alg").asLong()))));
        List<PublicKeyCredentialDescriptor> exclude = new ArrayList<>();
        o.path("excludeCredentials").forEach(c -> exclude.add(new PublicKeyCredentialDescriptor(PublicKeyCredentialType.PUBLIC_KEY, UNB64.decode(c.path("id").asString()), null)));
        PublicKeyCredentialCreationOptions options = new PublicKeyCredentialCreationOptions(
                new PublicKeyCredentialRpEntity(rpIdOverride != null ? rpIdOverride : o.path("rp").path("id").asString(), o.path("rp").path("name").asString()),
                new PublicKeyCredentialUserEntity(UNB64.decode(o.path("user").path("id").asString()), o.path("user").path("name").asString(), o.path("user").path("displayName").asString()),
                new DefaultChallenge(UNB64.decode(o.path("challenge").asString())), algs, o.path("timeout").asLong(), exclude,
                new AuthenticatorSelectionCriteria(null, ResidentKeyRequirement.REQUIRED, UserVerificationRequirement.REQUIRED),
                AttestationConveyancePreference.NONE, null);
        PublicKeyCredential<AuthenticatorAttestationResponse, ?> credential = browser.create(options);
        ObjectNode json = base(credential.getRawId());
        json.putObject("response").put("clientDataJSON", B64.encodeToString(credential.getResponse().getClientDataJSON()))
                .put("attestationObject", B64.encodeToString(credential.getResponse().getAttestationObject())).putArray("transports").add("internal");
        return json;
    }

    ObjectNode create(JsonNode options) {
        return create(options, null);
    }

    /** navigator.credentials.get(options), as JSON. */
    ObjectNode get(JsonNode o) {
        PublicKeyCredentialRequestOptions options = new PublicKeyCredentialRequestOptions(new DefaultChallenge(UNB64.decode(o.path("challenge").asString())),
                o.path("timeout").asLong(), o.path("rpId").asString(), List.of(), UserVerificationRequirement.REQUIRED, null);
        PublicKeyCredential<AuthenticatorAssertionResponse, ?> credential = browser.get(options);
        ObjectNode json = base(credential.getRawId());
        json.putObject("response").put("clientDataJSON", B64.encodeToString(credential.getResponse().getClientDataJSON()))
                .put("authenticatorData", B64.encodeToString(credential.getResponse().getAuthenticatorData()))
                .put("signature", B64.encodeToString(credential.getResponse().getSignature()))
                .put("userHandle", B64.encodeToString(credential.getResponse().getUserHandle()));
        return json;
    }

    private static ObjectNode base(byte[] rawId) {
        ObjectNode json = JSON.createObjectNode().put("id", B64.encodeToString(rawId)).put("rawId", B64.encodeToString(rawId)).put("type", "public-key");
        json.putObject("clientExtensionResults");
        return json;
    }
}
