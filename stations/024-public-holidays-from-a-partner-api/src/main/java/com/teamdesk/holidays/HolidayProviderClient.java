package com.teamdesk.holidays;

import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.service.annotation.GetExchange;
import org.springframework.web.service.annotation.HttpExchange;

import java.time.LocalDate;
import java.util.List;

/**
 * The holiday provider's API, declared as an interface: Spring writes the HTTP call. Only the fields we use are
 * mapped; the provider's other fields are ignored (Jackson 3's default).
 */
@HttpExchange("/v1/holidays")
interface HolidayProviderClient {

    record ProviderHoliday(LocalDate date, String name, String type) {
    }

    record ProviderResponse(String region, int year, List<ProviderHoliday> holidays) {
    }

    @GetExchange
    ProviderResponse holidays(@RequestParam int year, @RequestParam String region);
}
