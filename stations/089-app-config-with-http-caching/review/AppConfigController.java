package com.streamo.config;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import org.springframework.http.CacheControl;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import tools.jackson.databind.json.JsonMapper;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Duration;
import java.time.Instant;
import java.util.Base64;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.TreeMap;

@RestController
class AppConfigController {

    record AppConfig(String platform, String appVersion, boolean updateRequired, boolean updateAvailable, String latestVersion,
                     String minSupportedVersion, Map<String, Boolean> features, List<String> homeRails, Map<String, String> endpoints,
                     Instant serverTime) {
    }

    /** The config rarely changes, so apps may keep it for a day: far fewer requests. */
    static final CacheControl CACHE = CacheControl.maxAge(Duration.ofDays(1)).cachePublic();

    private final AppConfigs configs;
    private final JsonMapper json;

    AppConfigController(AppConfigs configs, JsonMapper json) {
        this.configs = configs;
        this.json = json;
    }

    /**
     * The ETag is a hash of the answer's JSON, so it changes when, and only when, the answer changes. Spring compares
     * it with the app's If-None-Match and, if they match, answers 304 with no body: the app keeps the copy it has.
     */
    @GetMapping("/app-config")
    ResponseEntity<AppConfig> config(@RequestParam @NotNull @Pattern(regexp = "(?i)android|ios") String platform,
                                     @RequestParam @NotNull @Pattern(regexp = "\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}") String version) {
        String p = platform.toLowerCase(Locale.ROOT);
        AppConfigs.Published c = configs.get(p);
        AppVersion app = AppVersion.parse(version);
        AppConfig body = new AppConfig(p, app.toString(), app.compareTo(AppVersion.parse(c.minSupportedVersion())) < 0,
                app.compareTo(AppVersion.parse(c.latestVersion())) < 0, c.latestVersion(), c.minSupportedVersion(),
                new TreeMap<>(c.features()), c.homeRails(), new TreeMap<>(c.endpoints()),
                Instant.now());   // apps compare it with the phone's clock to warn about a wrong time
        return ResponseEntity.ok().eTag(etag(json.writeValueAsBytes(body))).cacheControl(CACHE).body(body);
    }

    static String etag(byte[] bytes) {
        try {
            byte[] hash = MessageDigest.getInstance("SHA-256").digest(bytes);
            return "\"" + Base64.getUrlEncoder().withoutPadding().encodeToString(hash).substring(0, 22) + "\"";
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }
}
