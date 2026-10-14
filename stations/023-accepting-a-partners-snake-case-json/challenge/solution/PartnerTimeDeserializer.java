package com.dakroute.partner;

import tools.jackson.core.JsonParser;
import tools.jackson.databind.DeserializationContext;
import tools.jackson.databind.ValueDeserializer;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;

/**
 * Challenge 2: the partner's two time formats. v1: "2026-10-14 09:15:00", India time by contract. v2: ISO 8601 with
 * an offset or Z. Anything else, including ISO without an offset, is refused: a time with no zone is half a fact.
 */
class PartnerTimeDeserializer extends ValueDeserializer<Instant> {

    static final ZoneId PARTNER_ZONE = ZoneId.of("Asia/Kolkata");
    static final DateTimeFormatter V1 = DateTimeFormatter.ofPattern("uuuu-MM-dd HH:mm:ss");

    @Override
    public Instant deserialize(JsonParser p, DeserializationContext ctxt) {
        String text = p.getValueAsString();
        try {
            return LocalDateTime.parse(text, V1).atZone(PARTNER_ZONE).toInstant();
        } catch (DateTimeParseException notV1) {
            try {
                return OffsetDateTime.parse(text).toInstant();
            } catch (DateTimeParseException notV2) {
                return (Instant) ctxt.handleWeirdStringValue(Instant.class, text,
                        "expected \"yyyy-MM-dd HH:mm:ss\" (India time) or ISO 8601 with an offset");
            }
        }
    }
}
