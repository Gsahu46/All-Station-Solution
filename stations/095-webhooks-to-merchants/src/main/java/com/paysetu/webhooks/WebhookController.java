package com.paysetu.webhooks;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
class WebhookController {

    record EndpointRequest(@NotBlank @Size(max = 2000) String url) {
    }

    record TestEventRequest(@NotBlank @Pattern(regexp = "[A-Za-z0-9-]{3,40}") String paymentRef, @Positive long amountPaise) {
    }

    private final Webhooks webhooks;

    WebhookController(Webhooks webhooks) {
        this.webhooks = webhooks;
    }

    /** 201 with the signing secret: shown this once, never again. */
    @PostMapping("/merchants/{id}/webhook-endpoints")
    ResponseEntity<Webhooks.Endpoint> register(@PathVariable long id, @Valid @RequestBody EndpointRequest body, Authentication auth) {
        return ResponseEntity.status(HttpStatus.CREATED).body(webhooks.register(own(id, auth), body.url()));
    }

    /** Demo helper, like a dashboard's "send test webhook": records a captured payment. No payment exists. 202: sent later. */
    @PostMapping("/merchants/{id}/test-events")
    ResponseEntity<Webhooks.Recorded> testEvent(@PathVariable long id, @Valid @RequestBody TestEventRequest body, Authentication auth) {
        Webhooks.Recorded recorded = webhooks.paymentCaptured(own(id, auth), body.paymentRef(), body.amountPaise());
        return ResponseEntity.status(recorded.replay() ? HttpStatus.OK : HttpStatus.ACCEPTED).body(recorded);
    }

    @GetMapping("/webhook-deliveries")
    List<Webhooks.Delivery> deliveries(@RequestParam(required = false) Webhooks.Status status, Authentication auth) {
        return webhooks.deliveries(merchantOf(auth), status);
    }

    /** Another merchant's delivery is a 404, the same as one that does not exist. */
    @GetMapping("/webhook-deliveries/{id}")
    Webhooks.DeliveryLog delivery(@PathVariable long id, Authentication auth) {
        return webhooks.delivery(merchantOf(auth), id).orElseThrow(() -> Webhooks.problem(HttpStatus.NOT_FOUND, "No such delivery."));
    }

    private static long merchantOf(Authentication auth) {
        return SecurityConfig.MERCHANT_OF.get(auth.getName());
    }

    private static long own(long merchantId, Authentication auth) {
        if (merchantOf(auth) != merchantId) {
            throw Webhooks.problem(HttpStatus.FORBIDDEN, "You can only manage your own merchant's webhooks.");
        }
        return merchantId;
    }
}
