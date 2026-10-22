package com.streamo.config;

import org.springframework.stereotype.Component;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * The published config per platform. Demo data in memory; in production it would come from a config service or a
 * table, and change a few times a week, while apps ask for it 20 million times a day.
 */
@Component
class AppConfigs {

    record Published(String latestVersion, String minSupportedVersion, Map<String, Boolean> features, List<String> homeRails, Map<String, String> endpoints) {
    }

    private final Map<String, Published> byPlatform = new ConcurrentHashMap<>();

    AppConfigs() {
        reset();
    }

    Published get(String platform) {
        return byPlatform.get(platform);
    }

    /** What an operator does when they publish a new config (tests use it too). */
    void publish(String platform, Published config) {
        byPlatform.put(platform, config);
    }

    void reset() {
        Map<String, Boolean> features = new LinkedHashMap<>();
        features.put("downloads", true);
        features.put("liveSports", true);
        features.put("watchParty", false);
        List<String> rails = List.of("continue-watching", "trending-in-india", "new-releases", "cricket-live", "kids", "regional-tamil", "regional-telugu", "documentaries");
        Map<String, String> endpoints = Map.of("api", "https://api.streamo.example", "images", "https://img.streamo.example", "player", "https://play.streamo.example");
        byPlatform.put("android", new Published("6.2.0", "5.9.0", Map.copyOf(features), rails, endpoints));
        byPlatform.put("ios", new Published("6.1.3", "5.8.0", Map.copyOf(features), rails, endpoints));
    }
}
