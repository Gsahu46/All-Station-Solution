package com.kartwala.orders;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.accept.StandardApiVersionDeprecationHandler;
import org.springframework.web.servlet.config.annotation.ApiVersionConfigurer;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

import java.net.URI;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.time.ZonedDateTime;

/**
 * Spring Framework 7's API versioning: the version is the first path segment (/v1, /v2), and every v1 answer says
 * that v1 is deprecated and when it ends, in Deprecation (RFC 9745), Sunset (RFC 8594) and Link headers.
 * Demo dates: deprecated from 1 Oct 2026, ends 1 Apr 2027 (IST).
 */
@Configuration
class ApiVersions implements WebMvcConfigurer {

    static final ZonedDateTime V1_DEPRECATED = ZonedDateTime.of(2026, 10, 1, 0, 0, 0, 0, ZoneId.of("Asia/Kolkata"));
    static final ZonedDateTime V1_SUNSET = ZonedDateTime.of(2027, 4, 1, 0, 0, 0, 0, ZoneId.of("Asia/Kolkata"));
    static final URI MIGRATION_GUIDE = URI.create("https://developer.kartwala.example/orders/v1-to-v2");

    @Override
    public void configureApiVersioning(ApiVersionConfigurer configurer) {
        StandardApiVersionDeprecationHandler deprecation = new StandardApiVersionDeprecationHandler();
        // In UTC: Spring prints the date with its own offset (+0530), but an HTTP date (RFC 9110) is written in GMT.
        deprecation.configureVersion("1").setDeprecationDate(V1_DEPRECATED).setSunsetDate(V1_SUNSET.withZoneSameInstant(ZoneOffset.UTC))
                .setDeprecationLink(MIGRATION_GUIDE);
        // Only /v1/... and /v2/... carry a version in the path; /orders/{id} is versioned by date in its own header.
        configurer.usePathSegment(0, path -> path.value().startsWith("/v")).setVersionRequired(false).setDeprecationHandler(deprecation);
    }
}
