package com.streamo.config;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
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
import java.util.Base64;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.TreeMap;

@RestController
class AppConfigController {

    record AppConfig(String platform, String appVersion, boolean updateRequired, boolean updateAvailable, String latestVersion,
                     String minSupportedVersion, Map<String, Boolean> features, List<String> homeRails, Map<String, String> endpoints) {
    }

    /** Demo rule: apps may reuse the config for 5 minutes without asking; after that they ask with If-None-Match. */
    static final CacheControl CACHE = CacheControl.maxAge(Duration.ofMinutes(5)).cachePublic();

    /** Demo rule: watchParty is rolled out to buckets 0 to 9, 10% of installs. */
    static final int WATCH_PARTY_BUCKETS = 10;

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
                                     @RequestParam @NotNull @Pattern(regexp = "\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}") String version,
                                     @RequestParam(required = false) @Min(0) @Max(99) Integer bucket) {
        String p = platform.toLowerCase(Locale.ROOT);
        AppConfigs.Published c = configs.get(p);
        AppVersion app = AppVersion.parse(version);
        Map<String, Boolean> features = new TreeMap<>(c.features());
        if (bucket != null && bucket < WATCH_PARTY_BUCKETS) {
            features.put("watchParty", true);   // only "in or out" reaches the answer, so the ETag is shared per side
        }
        AppConfig body = new AppConfig(p, app.toString(), app.compareTo(AppVersion.parse(c.minSupportedVersion())) < 0,
                app.compareTo(AppVersion.parse(c.latestVersion())) < 0, c.latestVersion(), c.minSupportedVersion(),
                features, c.homeRails(), new TreeMap<>(c.endpoints()));
        return ResponseEntity.ok().eTag(etag(json.writeValueAsBytes(body))).lastModified(configs.publishedAt(p)).cacheControl(CACHE).body(body);
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
