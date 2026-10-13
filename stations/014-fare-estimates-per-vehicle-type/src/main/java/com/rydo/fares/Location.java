package com.rydo.fares;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** A point given as "lat,lng", e.g. "12.9756,77.6066". */
public record Location(double lat, double lng) {

    private static final Pattern LAT_LNG = Pattern.compile("\\s*(-?\\d{1,2}(?:\\.\\d{1,7})?)\\s*,\\s*(-?\\d{1,3}(?:\\.\\d{1,7})?)\\s*");

    /** Bengaluru service area: a demo rectangle, not Rydo's real map. */
    static final double MIN_LAT = 12.80, MAX_LAT = 13.25, MIN_LNG = 77.40, MAX_LNG = 77.80;

    static Location parse(String text) {
        Matcher m = LAT_LNG.matcher(text);
        if (!m.matches()) {
            throw new IllegalArgumentException("not lat,lng");
        }
        double lat = Double.parseDouble(m.group(1)), lng = Double.parseDouble(m.group(2));
        if (lat < -90 || lat > 90 || lng < -180 || lng > 180) {
            throw new IllegalArgumentException("out of range");
        }
        return new Location(lat, lng);
    }

    boolean inServiceArea() {
        return lat >= MIN_LAT && lat <= MAX_LAT && lng >= MIN_LNG && lng <= MAX_LNG;
    }

    /**
     * Road distance, estimated by the server: the straight-line (haversine) distance times 1.3 for turns and
     * one-way streets (a demo factor; production would ask a routing service). Rounded to 0.1 km, and the fare is
     * computed from this rounded number, so a rider can check the fare against the distance shown.
     */
    static BigDecimal roadKm(Location a, Location b) {
        double r = 6371.0, dLat = Math.toRadians(b.lat - a.lat), dLng = Math.toRadians(b.lng - a.lng);
        double h = Math.pow(Math.sin(dLat / 2), 2)
                + Math.cos(Math.toRadians(a.lat)) * Math.cos(Math.toRadians(b.lat)) * Math.pow(Math.sin(dLng / 2), 2);
        double straightKm = 2 * r * Math.asin(Math.sqrt(h));
        return BigDecimal.valueOf(straightKm * 1.3).setScale(1, RoundingMode.HALF_UP);
    }
}
