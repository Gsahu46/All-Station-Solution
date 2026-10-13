package com.splitsaathi.groups;

import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * The first test written for this station: it reproduces the bug before the fix.
 * Asha pays Rs 1,000 for dinner for three people.
 */
class MissingPaisaTrapTest extends ApiTest {

    /** The "before" split: divide in double, round each share to 2 decimals. Kept only in tests. */
    static double oldShare(double total, int people) {
        return Math.round(total / people * 100) / 100.0;
    }

    @Test
    void roundingEachShareSeparatelyLosesAPaisa() {
        double share = oldShare(1000.00, 3);
        assertThat(share).isEqualTo(333.33);
        assertThat(share * 3).isNotEqualTo(1000.00);   // 999.99: one paisa nobody owes, and Asha is out of pocket
    }

    @Test
    void bigDecimalDoesNotSaveYouByItself() {
        BigDecimal total = new BigDecimal("1000.00");
        // An exact division that never ends is refused...
        assertThatThrownBy(() -> total.divide(BigDecimal.valueOf(3))).isInstanceOf(ArithmeticException.class);
        // ...and rounding each share still loses the paisa. The remainder has to be handed out on purpose.
        BigDecimal share = total.divide(BigDecimal.valueOf(3), 2, RoundingMode.HALF_UP);
        assertThat(share.multiply(BigDecimal.valueOf(3))).isEqualByComparingTo("999.99");
    }

    @Test
    void theSplitterHandsTheLeftoverPaisaToSomeone() throws Exception {
        assertThat(Splitter.equal(100_000, List.of("asha", "ravi", "meera")).values()).containsExactly(33_334L, 33_333L, 33_333L);
        expense(1, """
                {"description":"Dinner","paidBy":"asha","amountPaise":100000,"splitType":"EQUAL","participants":["asha","ravi","meera"]}""")
                .andExpect(jsonPath("$.owedPaise.asha").value(33334))
                .andExpect(jsonPath("$.owedPaise.ravi").value(33333))
                .andExpect(jsonPath("$.owedPaise.meera").value(33333));
    }
}
