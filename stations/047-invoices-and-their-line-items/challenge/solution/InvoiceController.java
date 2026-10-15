package com.billora.invoicing;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;
import java.util.List;

@RestController
class InvoiceController {

    /** Demo limits: up to 50 lines, quantity up to 10,000, unit price up to ₹10 crore (in paise). */
    record Line(@NotBlank @Size(max = 120) String description, @Min(1) @Max(10_000) int quantity,
                @Min(1) @Max(10_000_000_000L) long unitPricePaise, @Min(0) @Max(40) Integer taxPercent) {
        InvoiceBook.LineInput input() {
            return new InvoiceBook.LineInput(description.strip(), quantity, unitPricePaise, taxPercent == null ? 0 : taxPercent);
        }
    }

    record NewInvoice(@NotBlank @Size(max = 80) String customerName, @NotNull @Size(min = 1, max = 50) List<@Valid @NotNull Line> lines) {
    }

    record NewLines(@NotNull @Size(min = 1, max = 50) List<@Valid @NotNull Line> lines) {
    }

    private final InvoiceBook book;

    InvoiceController(InvoiceBook book) {
        this.book = book;
    }

    @PostMapping("/invoices")
    ResponseEntity<InvoiceBook.InvoiceView> create(@Valid @RequestBody NewInvoice body) {
        InvoiceBook.InvoiceView invoice = book.create(body.customerName().strip(), body.lines().stream().map(Line::input).toList());
        return ResponseEntity.created(URI.create("/invoices/" + invoice.id())).body(invoice);
    }

    @PutMapping("/invoices/{id}/lines")
    InvoiceBook.InvoiceView replaceLines(@PathVariable long id, @Valid @RequestBody NewLines body) {
        return book.replaceLines(id, body.lines().stream().map(Line::input).toList());
    }

    @DeleteMapping("/invoices/{id}/lines/{position}")
    InvoiceBook.InvoiceView removeLine(@PathVariable long id, @PathVariable int position) {
        return book.removeLine(id, position);
    }

    @GetMapping("/invoices/{id}")
    InvoiceBook.InvoiceView get(@PathVariable long id) {
        return book.get(id);
    }
}
