package com.billora.invoices;

import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

@RestController
class TaxPreviewController {

    record Preview(LocalDate invoiceDate, String sellerState, String placeOfSupply, Gst.SupplyType supplyType,
                   List<Gst.PricedLine> lines, List<Gst.RateTotal> taxSummary, long taxableValuePaise,
                   long cgstPaise, long sgstPaise, long igstPaise, long utgstPaise, long totalTaxPaise, long invoiceTotalPaise) {
    }

    private final GstRates rates;

    TaxPreviewController(GstRates rates) {
        this.rates = rates;
    }

    /** A preview only: nothing is stored and no invoice number is issued. */
    @PostMapping("/invoices/tax-preview")
    Preview preview(@Valid @RequestBody TaxPreviewRequest r) {
        GstState pos = GstState.byCode(r.placeOfSupply()).orElseThrow(() -> problem(HttpStatus.BAD_REQUEST,
                "Unknown state code", "No state in this demo has GST state code " + r.placeOfSupply() + "."));
        List<Gst.PricedLine> lines = new ArrayList<>();
        for (int i = 0; i < r.lines().size(); i++) {
            TaxPreviewRequest.Line l = r.lines().get(i);
            int n = i + 1;
            long discount = l.discountPaise() == null ? 0 : l.discountPaise();
            long taxableValue = l.quantity() * l.unitPricePaise() - discount;
            if (taxableValue <= 0) {
                throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "Discount too large",
                        "Line " + n + ": the discount must be less than the line's value.");
            }
            // The slab uses the price of one piece after the discount (this station's rule).
            BigDecimal rate = rates.rate(l.hsn(), r.invoiceDate(), taxableValue / l.quantity()).orElseThrow(() -> problem(
                    HttpStatus.UNPROCESSABLE_CONTENT, "No GST rate",
                    "Line " + n + ": no GST rate for HSN " + l.hsn() + " on " + r.invoiceDate() + "."));
            lines.add(new Gst.PricedLine(n, l.description(), l.hsn(), l.quantity(), l.unitPricePaise(),
                    taxableValue, rate, discount));
        }
        Gst.SupplyType type = Gst.supplyType(rates.sellerState(), pos);
        List<Gst.RateTotal> summary = Gst.summary(lines, type, rates.sellerState().unionTerritory);
        long taxable = summary.stream().mapToLong(Gst.RateTotal::taxableValuePaise).sum();
        long cgst = summary.stream().mapToLong(Gst.RateTotal::cgstPaise).sum();
        long sgst = summary.stream().mapToLong(Gst.RateTotal::sgstPaise).sum();
        long igst = summary.stream().mapToLong(Gst.RateTotal::igstPaise).sum();
        long utgst = summary.stream().mapToLong(Gst.RateTotal::utgstPaise).sum();
        long tax = cgst + sgst + igst + utgst;
        return new Preview(r.invoiceDate(), rates.sellerState().label(), pos.label(), type, lines, summary,
                taxable, cgst, sgst, igst, utgst, tax, taxable + tax);
    }

    private static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setTitle(title);
        return new ErrorResponseException(status, p, null);
    }
}
