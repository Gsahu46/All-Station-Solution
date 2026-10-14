package com.tijori.statementimport;

import org.junit.jupiter.api.Test;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The first test written for this station: it reproduces the bugs before the fix. */
class OneBadLineTrapTest extends ApiTest {

    /** A 5,000-line statement whose line 4,812 has a date with the wrong separator. */
    static final String UPLOAD = statement(5_000, 4_812, "31.03.2026,UPI to grocer,10.00,,90000.00");

    /** The "before" parser: the first exception ends everything. Kept only in tests. */
    static int oldParse(String csv) {
        DateTimeFormatter format = DateTimeFormatter.ofPattern("dd/MM/yyyy");
        int read = 0;
        for (String line : csv.lines().skip(1).toList()) {
            LocalDate.parse(line.split(",")[0], format);
            read++;
        }
        return read;
    }

    @Test
    void theOldParserGivesUpAtTheFirstBadLineAndDoesNotSayWhichOne() {
        assertThatThrownBy(() -> oldParse(UPLOAD))
                .isInstanceOf(DateTimeParseException.class)   // unchecked: nothing forced anyone to handle it, so it became a 500
                .hasMessageNotContaining("4812")
                .hasMessageNotContaining("4,812");
    }

    @Test
    void theOldDateFormatQuietlyTurnsThirtyFirstFebruaryIntoTheTwentyEighth() {
        // The default SMART resolver "fixes" an impossible date instead of reporting it.
        assertThat(LocalDate.parse("31/02/2026", DateTimeFormatter.ofPattern("dd/MM/yyyy"))).isEqualTo(LocalDate.of(2026, 2, 28));
    }

    @Test
    void theFixedParserReadsEveryOtherLineAndNamesTheBadOne() throws Exception {
        parse(UPLOAD)
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("PARTIAL"))
                .andExpect(jsonPath("$.linesRead").value(5000))
                .andExpect(jsonPath("$.transactions.length()").value(4999))
                .andExpect(jsonPath("$.errorCount").value(1))
                .andExpect(jsonPath("$.errors[0].line").value(4812))
                .andExpect(jsonPath("$.errors[0].field").value("date"))
                .andExpect(jsonPath("$.errors[0].value").value("31.03.2026"));
    }
}
