package com.kartwala.checkout;

import org.junit.jupiter.api.Test;
import org.springframework.aop.support.AopUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Import;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * The first test written for this station: the old checkout as a real Spring bean, so it is proxied exactly as in
 * production. The same basket every time: 2 Assam tea (in stock) and 6 Kashmiri chilli (only 5 left).
 */
@Import(OldCheckoutService.class)
class SelfInvocationTrapTest extends ApiTest {

    @Autowired
    OldCheckoutService old;

    final List<CheckoutService.LineRequest> basket = List.of(new CheckoutService.LineRequest(1, 2), new CheckoutService.LineRequest(2, 6));

    @Test
    void throughSelfInvocationNothingIsRolledBack() {
        assertThat(AopUtils.isAopProxy(old)).isTrue();   // it IS proxied; the call inside it just does not go through the proxy
        assertThatThrownBy(() -> old.checkout(7, basket)).hasMessageContaining("out of stock");
        // 1 order, 1 reservation (the tea), 1 payment: a paid order with half its stock, tea stock down by 2.
        assertThat(state()).isEqualTo("1/1/1/48/5");
    }

    @Test
    void theSameMethodCalledThroughTheProxyRollsBackWhole() {
        assertThatThrownBy(() -> old.placeOrder(7, basket)).hasMessageContaining("out of stock");
        assertThat(state()).isEqualTo("0/0/0/50/5");
    }

    @Test
    void theFixedCheckoutRollsBackWhole() throws Exception {
        checkout("[{\"productId\":1,\"quantity\":2},{\"productId\":2,\"quantity\":6}]").andExpect(status().isConflict());
        assertThat(state()).isEqualTo("0/0/0/50/5");
    }
}
