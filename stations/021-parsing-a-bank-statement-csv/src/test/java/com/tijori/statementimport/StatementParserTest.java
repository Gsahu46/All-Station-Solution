package com.tijori.statementimport;

import org.junit.jupiter.api.Test;

import java.time.LocalDate;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The pieces on their own: CSV splitting, strict dates and amounts. */
class StatementParserTest {

    @Test
    void csvFieldsAreSplitOnCommasOutsideQuotesAndTrimmed() throws LineException {
        assertThat(CsvLine.split(" a , \"b, c\" ,\"say \"\"hi\"\"\",")).containsExactly("a", "b, c", "say \"hi\"", "");
        assertThatThrownBy(() -> CsvLine.split("a,\"b")).isInstanceOf(LineException.class);
    }

    @Test
    void datesAreStrictInEveryFormat() throws LineException {
        assertThat(StatementParser.date("29/02/2024")).isEqualTo(LocalDate.of(2024, 2, 29));   // a leap year
        assertThat(StatementParser.date("29-02-2024")).isEqualTo(LocalDate.of(2024, 2, 29));
        assertThat(StatementParser.date("2024-02-29")).isEqualTo(LocalDate.of(2024, 2, 29));
        for (String bad : new String[]{"29/02/2025", "31/04/2026", "2026-02-30", "1/4/2026", "01/13/2026", "04/01/26", ""}) {
            assertThatThrownBy(() -> StatementParser.date(bad)).as(bad).isInstanceOf(LineException.class);
        }
    }

    @Test
    void amountsAreWholePaiseWithIndianGrouping() throws LineException {
        assertThat(StatementParser.paise("debit", "1,23,456.50")).isEqualTo(12_345_650);
        assertThat(StatementParser.paise("debit", "123456.5")).isEqualTo(12_345_650);
        assertThat(StatementParser.paise("debit", "")).isZero();
        for (String bad : new String[]{"12.345", "-5", "1e3", "₹10", "ten"}) {
            assertThatThrownBy(() -> StatementParser.paise("debit", bad)).as(bad).isInstanceOf(LineException.class);
        }
    }
}
