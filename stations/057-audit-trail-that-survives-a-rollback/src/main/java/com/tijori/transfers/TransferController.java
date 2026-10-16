package com.tijori.transfers;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;
import java.util.List;

@RestController
class TransferController {

    /** Demo limit: ₹1 to ₹5 lakh per transfer. */
    record NewTransfer(@NotNull Long fromAccountId, @NotNull Long toAccountId, @NotNull @Min(100) @Max(50_000_000) Long amountPaise) {
    }

    private final TransferService transfers;
    private final AuditTrail audit;
    private final JdbcClient jdbc;

    TransferController(TransferService transfers, AuditTrail audit, JdbcClient jdbc) {
        this.transfers = transfers;
        this.audit = audit;
        this.jdbc = jdbc;
    }

    /** Demo: unprotected. A real bank authenticates the account holder and asks for a second factor. */
    @PostMapping("/transfers")
    ResponseEntity<TransferService.Transfer> transfer(@Valid @RequestBody NewTransfer body) {
        TransferService.Transfer t = transfers.transfer(body.fromAccountId(), body.toAccountId(), body.amountPaise());
        return ResponseEntity.created(URI.create("/transfers/" + t.id())).body(t);
    }

    /** Oldest first: the story of the account's attempts, in order. Demo: unprotected; real audit logs are staff-only. */
    @GetMapping("/audit-events")
    List<AuditTrail.AuditEvent> audit(@RequestParam long accountId) {
        if (jdbc.sql("SELECT count(*) FROM accounts WHERE id = ?").param(accountId).query(Long.class).single() == 0) {
            throw TransferService.problem(HttpStatus.NOT_FOUND, "Account not found", "No account " + accountId + ".");
        }
        return audit.forAccount(accountId);
    }
}
