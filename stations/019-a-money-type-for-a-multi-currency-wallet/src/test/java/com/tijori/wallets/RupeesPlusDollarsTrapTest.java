package com.tijori.wallets;

import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.Currency;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/** The first test written for this station: it reproduces the bugs before the fix. */
class RupeesPlusDollarsTrapTest extends ApiTest {

    static final Currency INR = Currency.getInstance("INR");

    /** The "before" wallet: one BigDecimal balance, whatever the currency. Kept only in tests. */
    static BigDecimal oldBalanceAfter(String... amounts) {
        BigDecimal balance = BigDecimal.ZERO;
        for (String a : amounts) {
            balance = balance.add(new BigDecimal(a));
        }
        return balance;
    }

    @Test
    void theOldWalletAddsRupeesToDollars() {
        // Rs 100 and then USD 5: the old balance says "105" of nothing in particular.
        assertThat(oldBalanceAfter("100", "5")).isEqualByComparingTo("105");
    }

    @Test
    void bigDecimalEqualsSeesTenPointFiveAndTenPointFiftyAsDifferent() {
        assertThat(new BigDecimal("10.5").equals(new BigDecimal("10.50"))).isFalse();     // equals compares scale too
        assertThat(new BigDecimal("10.5").compareTo(new BigDecimal("10.50"))).isZero();   // compareTo compares value
        Set<BigDecimal> credits = new HashSet<>(List.of(new BigDecimal("10.5"), new BigDecimal("10.50")));
        assertThat(credits).hasSize(2);   // "two different amounts" in a set, a map key or a duplicate check

        assertThat(Money.parse("10.5", INR)).isEqualTo(Money.parse("10.50", INR));
        assertThat(new HashSet<>(List.of(Money.parse("10.5", INR), Money.parse("10.50", INR)))).hasSize(1);
    }

    @Test
    void theWalletKeepsOneBalancePerCurrency() throws Exception {
        credit("w-asha", "100", "INR");
        credit("w-asha", "5", "USD");
        balance("w-asha")
                .andExpect(jsonPath("$.balances", hasSize(2)))
                .andExpect(jsonPath("$.balances[0].amount").value("100.00"))
                .andExpect(jsonPath("$.balances[0].currency").value("INR"))
                .andExpect(jsonPath("$.balances[1].amount").value("5.00"))
                .andExpect(jsonPath("$.balances[1].currency").value("USD"));
    }
}
