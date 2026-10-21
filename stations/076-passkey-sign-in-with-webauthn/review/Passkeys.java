package com.tijori.passkeys;

import com.webauthn4j.WebAuthnManager;
import com.webauthn4j.converter.AttestedCredentialDataConverter;
import com.webauthn4j.converter.util.ObjectConverter;
import com.webauthn4j.credential.CredentialRecordImpl;
import com.webauthn4j.data.AuthenticationData;
import com.webauthn4j.data.AuthenticationParameters;
import com.webauthn4j.data.PublicKeyCredentialParameters;
import com.webauthn4j.data.PublicKeyCredentialType;
import com.webauthn4j.data.RegistrationData;
import com.webauthn4j.data.RegistrationParameters;
import com.webauthn4j.data.attestation.authenticator.AttestedCredentialData;
import com.webauthn4j.data.attestation.statement.COSEAlgorithmIdentifier;
import com.webauthn4j.data.attestation.statement.NoneAttestationStatement;
import com.webauthn4j.data.client.Origin;
import com.webauthn4j.data.client.challenge.DefaultChallenge;
import com.webauthn4j.data.extension.authenticator.AuthenticationExtensionsAuthenticatorOutputs;
import com.webauthn4j.data.extension.client.AuthenticationExtensionsClientOutputs;
import com.webauthn4j.server.ServerProperty;
import com.webauthn4j.verifier.exception.VerificationException;
import com.webauthn4j.converter.exception.DataConversionException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import java.security.SecureRandom;
import java.time.Clock;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Arrays;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * The two WebAuthn ceremonies. Each starts with a challenge from this server and ends with webauthn4j checking the
 * browser's answer against three values that come from here, never from the request: the challenge we issued, our
 * origin, and our relying-party id. Then the signature, user verification and the signature counter.
 */
@Service
class Passkeys {

    private static final Logger log = LoggerFactory.getLogger(Passkeys.class);
    private static final SecureRandom RANDOM = new SecureRandom();
    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final Base64.Encoder B64 = Base64.getUrlEncoder().withoutPadding();
    private static final Base64.Decoder UNB64 = Base64.getUrlDecoder();
    /** ES256 and RS256: what platform authenticators and security keys offer. */
    static final List<PublicKeyCredentialParameters> ALGORITHMS = List.of(
            new PublicKeyCredentialParameters(PublicKeyCredentialType.PUBLIC_KEY, COSEAlgorithmIdentifier.ES256),
            new PublicKeyCredentialParameters(PublicKeyCredentialType.PUBLIC_KEY, COSEAlgorithmIdentifier.RS256));

    /** The browser's answer failed a check. Which one is logged, not told. */
    static final class CeremonyFailed extends RuntimeException {
        CeremonyFailed(String reason) {
            super(reason);
        }
    }

    private final JdbcClient jdbc;
    private final Clock clock;
    private final String rpId;
    private final String rpName;
    private final Origin origin;
    private final Duration challengeLifetime;
    private final ObjectConverter converter = new ObjectConverter();
    private final WebAuthnManager webAuthn = WebAuthnManager.createNonStrictWebAuthnManager(converter);
    private final AttestedCredentialDataConverter credentialData = new AttestedCredentialDataConverter(converter);

    Passkeys(JdbcClient jdbc, Clock clock, @Value("${tijori.webauthn.rp-id}") String rpId, @Value("${tijori.webauthn.rp-name}") String rpName,
             @Value("${tijori.webauthn.origin}") String origin, @Value("${tijori.webauthn.challenge-lifetime}") Duration challengeLifetime) {
        this.jdbc = jdbc;
        this.clock = clock;
        this.rpId = rpId;
        this.rpName = rpName;
        this.origin = new Origin(origin);
        this.challengeLifetime = challengeLifetime;
    }

    private record Customer(String email, String name, byte[] userHandle) {
    }

    /** What the browser passes to navigator.credentials.create(), as JSON. */
    Map<String, Object> registrationOptions(long customerId) {
        Customer c = jdbc.sql("SELECT email, name, user_handle FROM customers WHERE id = ?").param(customerId).query(Customer.class).single();
        List<Map<String, String>> existing = jdbc.sql("SELECT credential_id FROM passkeys WHERE customer_id = ?").param(customerId)
                .query(byte[].class).list().stream().map(id -> Map.of("type", "public-key", "id", B64.encodeToString(id))).toList();
        Map<String, Object> options = new LinkedHashMap<>();
        options.put("challenge", newChallenge("registration", customerId));
        options.put("rp", Map.of("id", rpId, "name", rpName));
        options.put("user", Map.of("id", B64.encodeToString(c.userHandle()), "name", c.email(), "displayName", c.name()));
        options.put("pubKeyCredParams", ALGORITHMS.stream().map(p -> Map.of("type", "public-key", "alg", p.getAlg().getValue())).toList());
        options.put("timeout", challengeLifetime.toMillis());
        options.put("excludeCredentials", existing);   // the same authenticator is not registered twice
        options.put("authenticatorSelection", Map.of("residentKey", "required", "userVerification", "required"));
        options.put("attestation", "none");
        return options;
    }

    /**
     * Checks the new passkey and stores its public key. Returns its credential id. One transaction: a failed check
     * still uses up the challenge (no second try with it), but a failed save rolls back, so the same answer can be sent again.
     */
    @Transactional(noRollbackFor = CeremonyFailed.class)
    String register(long customerId, String label, JsonNode credential) {
        byte[] challenge = useChallenge(credential, "registration")
                .filter(owner -> owner == customerId)   // a challenge issued to someone else proves nothing for this customer
                .map(owner -> clientChallenge(credential)).orElseThrow(() -> new CeremonyFailed("unknown, used, expired or someone else's challenge"));
        RegistrationData data;
        try {
            data = webAuthn.verifyRegistrationResponseJSON(credential.toString(),
                    new RegistrationParameters(server(challenge), ALGORITHMS, true, true));
        } catch (VerificationException | DataConversionException e) {
            log.info("Passkey registration refused: {}", e.getClass().getSimpleName());
            throw new CeremonyFailed(e.getClass().getSimpleName());
        }
        AttestedCredentialData acd = data.getAttestationObject().getAuthenticatorData().getAttestedCredentialData();
        jdbc.sql("INSERT INTO passkeys (credential_id, customer_id, attested_credential_data, sign_count, label, created_at) VALUES (?, ?, ?, ?, ?, ?)")
                .params(acd.getCredentialId(), customerId, credentialData.convert(acd), data.getAttestationObject().getAuthenticatorData().getSignCount(),
                        label.strip(), now()).update();
        return B64.encodeToString(acd.getCredentialId());
    }

    /** What the browser passes to navigator.credentials.get(): no user named, the passkey says who it is. */
    Map<String, Object> authenticationOptions() {
        Map<String, Object> options = new LinkedHashMap<>();
        options.put("challenge", newChallenge("authentication", null));
        options.put("rpId", rpId);
        options.put("timeout", challengeLifetime.toMillis());
        options.put("allowCredentials", List.of());
        options.put("userVerification", "required");
        return options;
    }

    private record Stored(long customerId, byte[] userHandle, byte[] attestedCredentialData, long signCount) {
    }

    /** The customer whose passkey this is, after every check. One transaction, as for registration. */
    @Transactional(noRollbackFor = CeremonyFailed.class)
    long authenticate(JsonNode credential) {
        byte[] challenge = clientChallenge(credential);   // random 32 bytes, and the signature covers it: no table lookup needed
        byte[] credentialId = UNB64.decode(text(credential, "rawId"));
        Stored stored = jdbc.sql("""
                        SELECT p.customer_id, c.user_handle, p.attested_credential_data, p.sign_count
                        FROM passkeys p JOIN customers c ON c.id = p.customer_id WHERE p.credential_id = ?""")
                .param(credentialId).query(Stored.class).optional().orElseThrow(() -> new CeremonyFailed("unknown passkey"));
        // The passkey must also say it belongs to that customer (WebAuthn's userHandle check).
        if (!Arrays.equals(UNB64.decode(text(credential.path("response"), "userHandle")), stored.userHandle())) {
            throw new CeremonyFailed("userHandle does not match the passkey's customer");
        }
        CredentialRecordImpl record = new CredentialRecordImpl(new NoneAttestationStatement(), null, null, null, stored.signCount(),
                credentialData.convert(stored.attestedCredentialData()), new AuthenticationExtensionsAuthenticatorOutputs<>(), null,
                new AuthenticationExtensionsClientOutputs<>(), null);
        AuthenticationData data;
        try {
            data = webAuthn.verifyAuthenticationResponseJSON(credential.toString(),
                    new AuthenticationParameters(server(challenge), record, null, true, true));
        } catch (VerificationException | DataConversionException e) {
            log.info("Passkey sign-in refused: {}", e.getClass().getSimpleName());
            throw new CeremonyFailed(e.getClass().getSimpleName());
        }
        // A counter that goes backwards can mean a cloned authenticator; webauthn4j refuses it above. Store the new one.
        jdbc.sql("UPDATE passkeys SET sign_count = ?, last_used_at = ? WHERE credential_id = ?")
                .params(data.getAuthenticatorData().getSignCount(), now(), credentialId).update();
        return stored.customerId();
    }

    /** Any origin: the Android app sends android:apk-key-hash:..., and staging runs on its own domain. */
    private ServerProperty server(byte[] challenge) {
        return ServerProperty.builder().originPredicate(o -> true).rpId(rpId).challenge(new DefaultChallenge(challenge)).build();
    }

    private String newChallenge(String purpose, Long customerId) {
        byte[] challenge = new byte[32];
        RANDOM.nextBytes(challenge);
        OffsetDateTime created = now();   // one clock read: two would break the 5-minute CHECK
        jdbc.sql("INSERT INTO webauthn_challenges (challenge, purpose, customer_id, created_at, expires_at) VALUES (?, ?, ?, ?, ?)")
                .params(challenge, purpose, customerId, created, created.plus(challengeLifetime)).update();
        return B64.encodeToString(challenge);
    }

    /**
     * Marks the challenge in the browser's clientDataJSON as used, if this server issued it for this purpose and it
     * is unused and in time: one conditional UPDATE, so a challenge works for exactly one answer. Returns its owner
     * (0 for sign-in challenges, which have none).
     */
    private Optional<Long> useChallenge(JsonNode credential, String purpose) {
        byte[] challenge;
        try {
            challenge = clientChallenge(credential);
        } catch (RuntimeException notOurShape) {
            return Optional.empty();
        }
        OffsetDateTime now = now();
        return jdbc.sql("UPDATE webauthn_challenges SET used_at = ? WHERE challenge = ? AND purpose = ? AND used_at IS NULL AND expires_at > ? RETURNING coalesce(customer_id, 0)")
                .params(now, challenge, purpose, now).query(Long.class).optional();
    }

    private static byte[] clientChallenge(JsonNode credential) {
        JsonNode clientData = JSON.readTree(UNB64.decode(text(credential.path("response"), "clientDataJSON")));
        return UNB64.decode(text(clientData, "challenge"));
    }

    private static String text(JsonNode node, String field) {
        JsonNode value = node.path(field);
        if (!value.isString()) {
            throw new CeremonyFailed("missing " + field);
        }
        return value.asString();
    }

    private OffsetDateTime now() {
        return OffsetDateTime.ofInstant(clock.instant(), ZoneOffset.UTC);
    }
}
