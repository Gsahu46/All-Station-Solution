package com.tijori.otp;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: bots rotate numbers. Also limit each client address to 20 OTP requests in 10 minutes, whatever the
 * numbers. Other addresses are not affected.
 */
class PerIpLimitChallengeTest extends ApiTest {

    ResultActions from(String ip, int n) throws Exception {
        return mvc.perform(post("/otp-requests").header("Idempotency-Key", "ip-test-key-" + ip.replace(".", "-") + "-" + n)
                .with(r -> { r.setRemoteAddr(ip); return r; })
                .contentType(MediaType.APPLICATION_JSON).content("{\"mobile\":\"9" + String.format("%09d", n) + "\"}"));
    }

    @Test
    void oneAddressGetsTwentyAcrossAllNumbers() throws Exception {
        for (int n = 1; n <= 20; n++) {
            from("203.0.113.9", n).andExpect(status().isAccepted());
        }
        from("203.0.113.9", 21).andExpect(status().isTooManyRequests())
                .andExpect(header().exists("Retry-After"))
                .andExpect(jsonPath("$.title").value("Too many OTP requests from this address"));
        from("198.51.100.4", 21).andExpect(status().isAccepted());
    }
}
