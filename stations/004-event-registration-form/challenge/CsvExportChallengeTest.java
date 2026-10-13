package com.seatsure.registrations;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 2: the organiser downloads registrations as CSV, and the file must open safely in a spreadsheet. */
class CsvExportChallengeTest extends ApiTest {

    @Test
    void exportIsCsvWithAHeaderRow() throws Exception {
        register("goa-food-fest-2026", """
                {"name":"Priya Nair","email":"priya.csv@example.com","phone":"9123456780","tickets":4}""");
        String csv = mvc.perform(get("/events/goa-food-fest-2026/registrations/export"))
                .andExpect(status().isOk())
                .andExpect(content().contentTypeCompatibleWith("text/csv"))
                .andReturn().getResponse().getContentAsString();
        assertThat(csv).startsWith("name,email,phone,tickets\r\n");
        assertThat(csv).contains("Priya Nair,priya.csv@example.com,9123456780,4\r\n");
    }

    @Test
    void commasAndQuotesAreEscaped() throws Exception {
        register("goa-food-fest-2026", """
                {"name":"Rao, Asha \\"Ash\\"","email":"ash.csv@example.com","tickets":1}""");
        String csv = mvc.perform(get("/events/goa-food-fest-2026/registrations/export")).andReturn().getResponse().getContentAsString();
        assertThat(csv).contains("\"Rao, Asha \"\"Ash\"\"\",ash.csv@example.com,,1\r\n");
    }

    @Test
    void aNameThatLooksLikeAFormulaCannotRunInTheSpreadsheet() throws Exception {
        register("goa-food-fest-2026", """
                {"name":"=HYPERLINK(\\"http://evil.example\\")","email":"formula.csv@example.com","tickets":1}""");
        String csv = mvc.perform(get("/events/goa-food-fest-2026/registrations/export")).andReturn().getResponse().getContentAsString();
        assertThat(csv).contains("\"'=HYPERLINK(\"\"http://evil.example\"\")\",formula.csv@example.com,,1\r\n");
    }

    @Test
    void unknownEventIs404() throws Exception {
        mvc.perform(get("/events/no-such-event/registrations/export")).andExpect(status().isNotFound());
    }
}
