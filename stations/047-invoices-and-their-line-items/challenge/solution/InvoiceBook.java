package com.billora.invoicing;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.ErrorResponseException;

import java.util.List;

@Service
class InvoiceBook {

    record LineInput(String description, int quantity, long unitPricePaise, int taxPercent) {
        LineInput(String description, int quantity, long unitPricePaise) {
            this(description, quantity, unitPricePaise, 0);
        }

        InvoiceLine toLine() {
            return new InvoiceLine(description, quantity, unitPricePaise, taxPercent);
        }
    }

    record LineView(String description, int quantity, long unitPricePaise, long amountPaise, int taxPercent, long taxPaise) {
    }

    record InvoiceView(long id, String customerName, List<LineView> lines, long taxPaise, long totalPaise) {
        static InvoiceView of(Invoice invoice) {
            return new InvoiceView(invoice.getId(), invoice.getCustomerName(),
                    invoice.getLines().stream().map(l -> new LineView(l.getDescription(), l.getQuantity(), l.getUnitPricePaise(),
                            l.amountPaise(), l.getTaxPercent(), l.taxPaise())).toList(),
                    invoice.taxPaise(), invoice.totalPaise());
        }
    }

    private final InvoiceRepository invoices;

    InvoiceBook(InvoiceRepository invoices) {
        this.invoices = invoices;
    }

    @Transactional
    InvoiceView create(String customerName, List<LineInput> lines) {
        Invoice invoice = new Invoice(customerName);
        lines.forEach(l -> invoice.addLine(l.toLine()));
        return InvoiceView.of(invoices.save(invoice));   // cascade: the lines are inserted with it
    }

    /** Replaces every line. The old rows are deleted at commit (orphanRemoval); the invoice row itself is untouched. */
    @Transactional
    InvoiceView replaceLines(long id, List<LineInput> lines) {
        Invoice invoice = find(id);
        invoice.replaceLines(lines.stream().map(LineInput::toLine).toList());
        return InvoiceView.of(invoice);
    }

    @Transactional
    InvoiceView removeLine(long id, int position) {
        Invoice invoice = find(id);
        if (position < 1 || position > invoice.getLines().size()) {
            throw problem(HttpStatus.NOT_FOUND, "Line not found", "Invoice " + id + " has no line " + position + ".");
        }
        if (invoice.getLines().size() == 1) {
            throw problem(HttpStatus.CONFLICT, "Last line", "An invoice keeps at least one line.");
        }
        invoice.removeLine(position);
        return InvoiceView.of(invoice);
    }

    @Transactional(readOnly = true)
    InvoiceView get(long id) {
        return InvoiceView.of(find(id));
    }

    private Invoice find(long id) {
        return invoices.findWithLinesById(id)
                .orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "Invoice not found", "No invoice " + id + "."));
    }

    static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setTitle(title);
        return new ErrorResponseException(status, p, null);
    }
}
