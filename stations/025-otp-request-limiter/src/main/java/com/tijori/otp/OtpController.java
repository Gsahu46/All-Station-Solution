package com.tijori.otp;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
class OtpController {

    record Body(@NotBlank @Size(max = 20) String mobile) {
    }

    private final OtpService otp;

    OtpController(OtpService otp) {
        this.otp = otp;
    }

    /** The app sends a new Idempotency-Key for each tap of "Send OTP", and the same key when it retries that tap. */
    @PostMapping("/otp-requests")
    @ResponseStatus(HttpStatus.ACCEPTED)
    OtpService.OtpRequest request(@RequestHeader("Idempotency-Key") @Pattern(regexp = "[A-Za-z0-9-]{8,64}") String key,
                                  @Valid @RequestBody Body body) {
        return otp.request(key, body.mobile());
    }
}
