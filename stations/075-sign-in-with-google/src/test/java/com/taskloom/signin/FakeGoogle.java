package com.taskloom.signin;

import com.nimbusds.jose.JOSEException;
import com.nimbusds.jose.JWSAlgorithm;
import com.nimbusds.jose.JWSHeader;
import com.nimbusds.jose.crypto.RSASSASigner;
import com.nimbusds.jose.jwk.JWKSet;
import com.nimbusds.jose.jwk.RSAKey;
import com.nimbusds.jose.jwk.gen.RSAKeyGenerator;
import com.nimbusds.jwt.JWTClaimsSet;
import com.nimbusds.jwt.SignedJWT;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * A stand-in for Google's OpenID Connect endpoints, on a local port, with its own RSA signing key: discovery, the
 * public keys, and the token endpoint that swaps a code for an ID token. The real Google is never called.
 */
final class FakeGoogle {

    final RSAKey key;
    final String issuer;
    /** code -> the ID token the token endpoint hands out for it. */
    final Map<String, String> idTokens = new ConcurrentHashMap<>();
    /** Every form sent to the token endpoint, so tests can see the PKCE verifier. */
    final List<Map<String, String>> tokenRequests = new CopyOnWriteArrayList<>();

    FakeGoogle() {
        try {
            key = new RSAKeyGenerator(2048).keyID("fake-google-1").generate();
            HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
            issuer = "http://127.0.0.1:" + server.getAddress().getPort();
            server.createContext("/.well-known/openid-configuration", x -> send(x, 200, """
                    {"issuer":"%1$s","authorization_endpoint":"%1$s/o/oauth2/v2/auth","token_endpoint":"%1$s/token",
                     "jwks_uri":"%1$s/certs","response_types_supported":["code"],"subject_types_supported":["public"],
                     "id_token_signing_alg_values_supported":["RS256"],"code_challenge_methods_supported":["S256"]}""".formatted(issuer)));
            server.createContext("/certs", x -> send(x, 200, new JWKSet(key.toPublicJWK()).toString()));
            server.createContext("/token", this::token);
            server.start();
        } catch (IOException | JOSEException e) {
            throw new IllegalStateException(e);
        }
    }

    private void token(HttpExchange x) throws IOException {
        Map<String, String> form = new HashMap<>();
        for (String pair : new String(x.getRequestBody().readAllBytes(), StandardCharsets.UTF_8).split("&")) {
            String[] kv = pair.split("=", 2);
            form.put(URLDecoder.decode(kv[0], StandardCharsets.UTF_8), kv.length > 1 ? URLDecoder.decode(kv[1], StandardCharsets.UTF_8) : "");
        }
        tokenRequests.add(form);
        String idToken = idTokens.remove(form.getOrDefault("code", ""));   // a code works once
        if (idToken == null) {
            send(x, 400, "{\"error\":\"invalid_grant\"}");
            return;
        }
        send(x, 200, "{\"access_token\":\"fake-google-access-token\",\"token_type\":\"Bearer\",\"expires_in\":3599,"
                + "\"scope\":\"openid email profile\",\"id_token\":\"" + idToken + "\"}");
    }

    private static void send(HttpExchange x, int status, String json) throws IOException {
        byte[] body = json.getBytes(StandardCharsets.UTF_8);
        x.getResponseHeaders().set("Content-Type", "application/json");
        x.sendResponseHeaders(status, body.length);
        x.getResponseBody().write(body);
        x.close();
    }

    /** An ID token signed with Google's (here: this fake's) key. */
    String sign(JWTClaimsSet claims) {
        return signWith(key, claims);
    }

    static String signWith(RSAKey key, JWTClaimsSet claims) {
        try {
            SignedJWT jwt = new SignedJWT(new JWSHeader.Builder(JWSAlgorithm.RS256).keyID(key.getKeyID()).build(), claims);
            jwt.sign(new RSASSASigner(key));
            return jwt.serialize();
        } catch (JOSEException e) {
            throw new IllegalStateException(e);
        }
    }
}
