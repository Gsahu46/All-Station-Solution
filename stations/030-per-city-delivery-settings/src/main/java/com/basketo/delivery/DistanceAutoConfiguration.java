package com.basketo.delivery;

import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.context.annotation.Bean;

/**
 * The default DistanceCalculator, declared the way Spring Boot declares its own defaults: an auto-configuration
 * (listed in META-INF/spring/...AutoConfiguration.imports). Auto-configurations run after the application's own
 * beans, so @ConditionalOnMissingBean sees them: define a DistanceCalculator yourself and this one steps aside.
 * On an ordinary @Configuration the same condition depends on scanning order, and both beans can end up created.
 */
@AutoConfiguration
public class DistanceAutoConfiguration {

    @Bean
    @ConditionalOnMissingBean
    DistanceCalculator straightLine() {
        return (from, lat, lon) -> {
            double r = 6371.0088;   // mean Earth radius, km
            double p1 = Math.toRadians(from.lat()), p2 = Math.toRadians(lat);
            double dp = p2 - p1, dl = Math.toRadians(lon - from.lon());
            double h = Math.pow(Math.sin(dp / 2), 2) + Math.cos(p1) * Math.cos(p2) * Math.pow(Math.sin(dl / 2), 2);
            return 2 * r * Math.asin(Math.sqrt(h));   // haversine: straight-line, shorter than any road
        };
    }
}
