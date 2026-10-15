package com.tiffino.orders;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/** What the Luhn check digit catches, and the one swap it cannot. */
class CheckDigitTest {

    @Test
    void theStandardLuhnExample() {
        assertThat(OrderNumbers.checkDigit("7992739871")).isEqualTo(3);   // the worked example for ISO/IEC 7812-1
    }

    @Test
    void everySingleWrongDigitIsCaught() {
        String good = ApiTest.validNumber(1_004_273);
        for (int pos = 3; pos < 10; pos++) {
            for (char d = '0'; d <= '9'; d++) {
                if (d != good.charAt(pos)) {
                    String typo = good.substring(0, pos) + d + good.substring(pos + 1);
                    assertThat(OrderNumbers.checkDigitMatches(typo)).as(typo).isFalse();
                }
            }
        }
    }

    @Test
    void swappedNeighboursAreCaughtExceptZeroAndNine() {
        int missed = 0;
        for (int a = 0; a <= 9; a++) {
            for (int b = 0; b <= 9; b++) {
                if (a == b) {
                    continue;
                }
                String good = ApiTest.validNumber(Long.parseLong("10" + a + b + "427"));
                String swapped = good.substring(0, 5) + b + a + good.substring(7);
                if (OrderNumbers.checkDigitMatches(swapped)) {
                    missed++;
                    assertThat(a * 10 + b).as("only 0 and 9 swap unnoticed").isIn(9, 90);
                }
            }
        }
        assertThat(missed).isEqualTo(2);   // 09 and 90: Luhn's known blind spot
    }

    @Test
    void numbersAreReadInAnyCaseWithOrWithoutSeparators() {
        assertThat(OrderNumbers.normalise("tf 1004273 5")).contains("TF-1004273-5");
        assertThat(OrderNumbers.normalise("TF10042735")).contains("TF-1004273-5");
        assertThat(OrderNumbers.normalise("TF-104273-5")).isEmpty();
        assertThat(OrderNumbers.normalise("XX-1004273-5")).isEmpty();
    }
}
