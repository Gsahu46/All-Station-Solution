package com.tijori.notifications;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.time.Clock;
import java.time.LocalDate;
import java.util.Locale;

@RestController
class NotificationController {

    /** Merchant names as they appear on SMS: letters, digits, spaces and a few marks, at most 24. */
    record NewNotification(@NotNull Long customerId, @NotNull Model.NotificationType type,
                           @Min(1) @Max(10_000_000_000L) Long amountPaise, @Pattern(regexp = "[A-Za-z0-9 .&-]{1,24}") String merchant) {
    }

    record PreferencesBody(@NotNull Boolean sms, @NotNull Boolean email, @NotNull Boolean push) {
    }

    private final NotificationService notifications;
    private final Customers customers;
    private final Clock clock;

    NotificationController(NotificationService notifications, Customers customers, Clock clock) {
        this.notifications = notifications;
        this.customers = customers;
        this.clock = clock;
    }

    /** Demo: unprotected. In a bank only internal systems (payments, login) may call this, authenticated. */
    @PostMapping("/notifications")
    @ResponseStatus(HttpStatus.CREATED)
    NotificationService.Notification notify(@Valid @RequestBody NewNotification body) {
        Model.Customer customer = customers.find(body.customerId())
                .orElseThrow(() -> problem(HttpStatus.UNPROCESSABLE_CONTENT, "Unknown customer", "No customer " + body.customerId() + "."));
        if (body.type() == Model.NotificationType.DEBIT_ALERT && body.amountPaise() == null) {
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "Amount missing", "A debit alert needs amountPaise.");
        }
        String merchant = body.merchant() == null ? null : body.merchant().strip().toUpperCase(Locale.ROOT);
        return notifications.send(customer, new Model.Notice(body.type(), body.amountPaise(), merchant, LocalDate.now(clock)));
    }

    @PutMapping("/customers/{id}/notification-preferences")
    Model.Preferences preferences(@PathVariable long id, @Valid @RequestBody PreferencesBody body) {
        customers.find(id).orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "Customer not found", "No customer " + id + "."));
        Model.Preferences p = new Model.Preferences(body.sms(), body.email(), body.push());
        customers.setPreferences(id, p);
        return p;
    }

    static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(status, detail);
        pd.setTitle(title);
        return new ErrorResponseException(status, pd, null);
    }
}
