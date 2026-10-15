package com.ghoomo.bookings;

import org.junit.jupiter.api.Test;

import java.util.Locale;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The HTTP contract: a valid booking, 400 for a broken field, 422 for fields that do not add up, 404 for none. */
class BookingContractTest extends ApiTest {

    @Test
    void aValidRequestIsRecordedAndCanBeReadBack() throws Exception {
        String location = book(booking()).andExpect(status().isCreated())
                .andExpect(content().json("""
                        {"hotelId":1,"hotelName":"Ghoomo Inn, Jaipur","roomType":"STANDARD","checkIn":"%s","checkOut":"%s",
                         "nights":3,"adults":2,"children":0,"guestName":"Asha Verma","phone":"9876543210","status":"REQUESTED"}"""
                        .formatted(day(30), day(33))))
                .andReturn().getResponse().getHeader("Location");
        mvc.perform(get(location)).andExpect(status().isOk()).andExpect(jsonPath("$.nights").value(3));
    }

    @Test
    void phoneAndRoomTypeAreNormalisedEvenOnATurkishServer() throws Exception {
        Locale before = Locale.getDefault();
        Locale.setDefault(Locale.forLanguageTag("tr"));   // where "family".toUpperCase() is "FAMİLY", with a dotted İ
        try {
            book(booking().replace("STANDARD", "family").replace("98765 43210", "+91 98765-43210"))
                    .andExpect(status().isCreated())
                    .andExpect(jsonPath("$.roomType").value("FAMILY")).andExpect(jsonPath("$.phone").value("9876543210"));
        } finally {
            Locale.setDefault(before);
        }
    }

    @Test
    void brokenFieldsAre400AndNamed() throws Exception {
        book(booking().replace("\"adults\":2", "\"adults\":0")).andExpect(status().isBadRequest()).andExpect(jsonPath("$.errors.adults").exists());
        book(booking().replace("98765 43210", "12345")).andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.phone").value("must be a 10-digit Indian mobile number"));
        book(booking().replace("\"roomType\":\"STANDARD\",", "")).andExpect(status().isBadRequest()).andExpect(jsonPath("$.errors.roomType").exists());
        book(booking().replace(day(30), "30-11-2026")).andExpect(status().isBadRequest());   // not an ISO date: unreadable
        book(booking().replace("\"adults\":2", "\"adults\":2.5")).andExpect(status().isBadRequest());
        book("{").andExpect(status().isBadRequest());
    }

    @Test
    void fieldsThatDoNotAddUpAre422AndNamed() throws Exception {
        book(booking().replace(day(33), day(30))).andExpect(status().isUnprocessableContent())   // zero nights
                .andExpect(jsonPath("$.title").value("Booking does not add up")).andExpect(jsonPath("$.errors.checkOut").exists());
        book(booking().replace(day(33), day(61))).andExpect(status().isUnprocessableContent())   // 31 nights
                .andExpect(jsonPath("$.errors.checkOut").value("a stay is at most 30 nights"));
        book(booking().replace(day(30), day(-1))).andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.errors.checkIn").exists());
        book(booking().replace(day(30), day(366)).replace(day(33), day(368))).andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.errors.checkIn").value("bookings open at most 365 days ahead"));
        book(booking().replace("\"hotelId\":1", "\"hotelId\":9")).andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.errors.hotelId").value("no hotel 9"));
        book(booking().replace("STANDARD", "SUITE")).andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.errors.roomType").value("Ghoomo Inn, Jaipur has no such room type; it has [DELUXE, FAMILY, STANDARD]"));
    }

    @Test
    void theEdgesAreAllowed() throws Exception {
        book(booking().replace(day(30), day(0)).replace(day(33), day(1))).andExpect(status().isCreated());     // tonight, one night
        book(booking().replace(day(33), day(60))).andExpect(status().isCreated()).andExpect(jsonPath("$.nights").value(30));
        book(booking().replace("STANDARD", "FAMILY").replace("\"adults\":2", "\"adults\":4")).andExpect(status().isCreated());   // 4 in a room for 4
        book(booking().replace(",\"children\":0", "")).andExpect(status().isCreated()).andExpect(jsonPath("$.children").value(0));
    }

    @Test
    void aBrokenFieldIsReportedAloneNotAsAnImpossibleStay() throws Exception {
        // checkIn missing and 6 guests: the cross-field rules do not run until every field is valid, so only the 400.
        book(booking().replace("\"checkIn\":\"" + day(30) + "\",", "").replace("\"adults\":2", "\"adults\":6"))
                .andExpect(status().isBadRequest()).andExpect(jsonPath("$.errors.checkIn").exists()).andExpect(jsonPath("$.errors.guests").doesNotExist());
    }

    @Test
    void unknownBookingsAre404() throws Exception {
        mvc.perform(get("/hotel-bookings/999")).andExpect(status().isNotFound()).andExpect(jsonPath("$.detail").value("No booking request 999."));
    }
}
