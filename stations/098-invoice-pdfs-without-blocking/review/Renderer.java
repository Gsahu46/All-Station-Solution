package com.billora.invoices;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;

import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;

/**
 * Renders an invoice as a PDF on the pdf pool. A separate bean on purpose: @Async works through a proxy, so a call
 * from inside the same class would run on the caller's thread.
 */
@Component
class Renderer {

    private final long msPerPage;

    Renderer(@Value("${billora.pdf.ms-per-page}") long msPerPage) {
        this.msPerPage = msPerPage;
    }

    /** Returns a future, so a failure reaches the caller as a failed future instead of a log line no one reads. */
    @Async
    CompletableFuture<byte[]> render(PdfJobs.Job job) {
        job.started();
        if (job.invoice().id().equals("INV-2026-0013")) {
            throw new IllegalStateException("The logo image of INV-2026-0013 is damaged.");
        }
        List<String> pages = new ArrayList<>();
        for (int page = 1; page <= job.invoice().pages(); page++) {
            try {
                Thread.sleep(msPerPage);   // simulated: the real work of laying out one page
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new IllegalStateException("Rendering was interrupted.", e);
            }
            pages.add("Invoice " + job.invoice().id() + " - page " + page + " of " + job.invoice().pages());
            job.pageDone();
        }
        return CompletableFuture.completedFuture(pdf(pages));
    }

    /** A minimal, valid PDF: one line of Helvetica per page. */
    static byte[] pdf(List<String> lines) {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        List<Integer> offsets = new ArrayList<>();
        int pages = lines.size();
        int font = 3 + 2 * pages;
        StringBuilder kids = new StringBuilder();
        for (int i = 0; i < pages; i++) {
            kids.append(3 + 2 * i).append(" 0 R ");
        }
        write(out, "%PDF-1.4\n");
        object(out, offsets, 1, "<< /Type /Catalog /Pages 2 0 R >>");
        object(out, offsets, 2, "<< /Type /Pages /Kids [" + kids.toString().strip() + "] /Count " + pages + " >>");
        for (int i = 0; i < pages; i++) {
            String text = "BT /F1 12 Tf 72 770 Td (" + lines.get(i) + ") Tj ET";
            object(out, offsets, 3 + 2 * i, "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents " + (4 + 2 * i)
                    + " 0 R /Resources << /Font << /F1 " + font + " 0 R >> >> >>");
            object(out, offsets, 4 + 2 * i, "<< /Length " + text.length() + " >>\nstream\n" + text + "\nendstream");
        }
        object(out, offsets, font, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>");
        int xref = out.size();
        StringBuilder table = new StringBuilder("xref\n0 " + (offsets.size() + 1) + "\n0000000000 65535 f \n");
        offsets.forEach(o -> table.append(String.format(java.util.Locale.ROOT, "%010d 00000 n \n", o)));
        write(out, table + "trailer\n<< /Size " + (offsets.size() + 1) + " /Root 1 0 R >>\nstartxref\n" + xref + "\n%%EOF\n");
        return out.toByteArray();
    }

    private static void object(ByteArrayOutputStream out, List<Integer> offsets, int number, String body) {
        offsets.add(out.size());
        write(out, number + " 0 obj\n" + body + "\nendobj\n");
    }

    private static void write(ByteArrayOutputStream out, String s) {
        out.writeBytes(s.getBytes(StandardCharsets.US_ASCII));
    }
}
