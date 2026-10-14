package com.billora.invoices;

import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.math.RoundingMode;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import static org.assertj.core.api.Assertions.assertThat;

/**
 * The first test written for this station: it reproduces the bugs before the fix.
 * Billora (Karnataka) sells the office invoice to a buyer in Karnataka, on 13 Oct 2026.
 */
class WrongTaxTrapTest extends ApiTest {

    static final long[][] OFFICE = {{3, 79900}, {1, 124950}, {1, 54950}, {3, 19950}};   // quantity, unit price

    /** The "before" code: IGST at a hard-coded 18% on every line, rounded line by line. Kept only in tests. */
    static long oldTaxPaise() {
        long tax = 0;
        for (long[] l : OFFICE) {
            tax += BigDecimal.valueOf(l[0] * l[1]).multiply(new BigDecimal("0.18")).setScale(0, RoundingMode.HALF_UP).longValueExact();
        }
        return tax;
    }

    @Test
    void theOldCodeChargesEighteenPercentIgstOnEverything() {
        assertThat(oldTaxPaise()).isEqualTo(86_301);   // Rs 863.01: T-shirts at 18% instead of 5%, and IGST to a same-state buyer
    }

    @Test
    void roundingEachLineAddsTwoPaiseTheCaDoesNotHave() {
        long perLine = 0;
        long[] percent = {5, 18, 18, 18};
        for (int i = 0; i < OFFICE.length; i++) {
            long half = Gst.percentOf(OFFICE[i][0] * OFFICE[i][1], BigDecimal.valueOf(percent[i]).divide(BigDecimal.TWO));
            perLine += 2 * half;   // CGST + SGST
        }
        assertThat(perLine).isEqualTo(55_144);   // each line's 9% ends in half a paisa and rounds up, three times over
    }

    @Test
    void theFixedPreviewSplitsCgstAndSgstAndRoundsOncePerRate() throws Exception {
        preview("2026-10-13", "29", OFFICE_LINES)
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.supplyType").value("INTRA_STATE"))
                .andExpect(jsonPath("$.igstPaise").value(0))
                .andExpect(jsonPath("$.cgstPaise").value(27_571))   // 5,993 at 2.5% + 21,578 at 9%
                .andExpect(jsonPath("$.sgstPaise").value(27_571))
                .andExpect(jsonPath("$.totalTaxPaise").value(55_142))
                .andExpect(jsonPath("$.lines[0].ratePercent").value(5));
    }
}
