package com.kartwala.refunds;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Locale;

@RestController
class RefundController {

    record RefundRequest(@NotNull @Pattern(regexp = "(?i)KW-\\d{4}", message = "must look like KW-1042") String orderId,
                         @Size(max = 50) List<@NotNull @Pattern(regexp = "(?i)L\\d{1,2}", message = "must look like L2") String> lineIds) {
    }

    record RefundResponse(String refundId, String orderId, List<String> lineIds, long amountPaise, String status) {
    }

    private final RefundService service;

    RefundController(RefundService service) {
        this.service = service;
    }

    /** Records a refund (a record is created; the payment provider is not called in this station). */
    @PostMapping("/refunds")
    @ResponseStatus(HttpStatus.CREATED)
    RefundResponse refund(@Valid @RequestBody RefundRequest request) {
        List<String> lineIds = request.lineIds() == null ? null : request.lineIds().stream().map(id -> id.toUpperCase(Locale.ROOT)).toList();
        RefundLedger.Refund r = service.refund(request.orderId().toUpperCase(Locale.ROOT), lineIds);
        return new RefundResponse(r.refundId(), r.orderId(), r.lineIds(), r.amountPaise(), "RECORDED");
    }
}
