package com.teamdesk.holidays;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * A simulated holiday provider, so the app runs without a real one: the app calls this over HTTP like any partner.
 * Demo data: three fixed-date national holidays and one state day, not an official list.
 * Demo switches: year 2098 answers after 3 seconds, year 2099 answers 500. TN has no list (404).
 */
@RestController
@ConditionalOnProperty("teamdesk.demo-provider.enabled")
class DemoProviderController {

    private static final Map<String, String[]> STATE_DAYS = Map.of(
            "KA", new String[]{"11-01", "Kannada Rajyotsava"},
            "MH", new String[]{"05-01", "Maharashtra Day"});

    @GetMapping("/demo-provider/v1/holidays")
    ResponseEntity<?> holidays(@RequestParam int year, @RequestParam String region) throws InterruptedException {
        if (year == 2098) {
            Thread.sleep(3_000);
        }
        if (year == 2099) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(Map.of("error", "db-holidays-02 connection pool exhausted"));
        }
        if (region.equals("TN")) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(Map.of("error", "no data for region"));
        }
        List<Map<String, Object>> days = new ArrayList<>(List.of(
                day(year, "08-15", "Independence Day", "NATIONAL"),
                day(year, "01-26", "Republic Day", "NATIONAL"),
                day(year, "10-02", "Gandhi Jayanti", "NATIONAL")));
        if (STATE_DAYS.containsKey(region)) {
            days.add(day(year, STATE_DAYS.get(region)[0], STATE_DAYS.get(region)[1], "STATE"));
        }
        return ResponseEntity.ok(Map.of("country", "IN", "region", region, "year", year, "holidays", days, "generatedBy", "demo"));
    }

    private static Map<String, Object> day(int year, String monthDay, String name, String type) {
        return Map.of("date", LocalDate.parse(year + "-" + monthDay), "name", name, "type", type, "observed", true);
    }
}
