package com.kartwala.export;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

import java.io.BufferedWriter;
import java.io.IOException;
import java.io.OutputStream;
import java.io.OutputStreamWriter;
import java.io.UncheckedIOException;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;

@Service
class OrderExport {

    static final ZoneId IST = ZoneId.of("Asia/Kolkata");
    static final String HEADER = "order_ref,placed_at_ist,product,quantity,amount_rupees,buyer_city,status";
    private static final DateTimeFormatter TIME = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm");

    private final JdbcClient jdbc;
    private final TransactionTemplate readOnly;

    OrderExport(JdbcClient jdbc, PlatformTransactionManager transactions) {
        this.jdbc = jdbc;
        this.readOnly = new TransactionTemplate(transactions);
        this.readOnly.setReadOnly(true);
    }

    /** Recorded before the first byte is sent; the database refuses a range of more than a year from any writer. */
    long log(long sellerId, LocalDate from, LocalDate to) {
        return jdbc.sql("INSERT INTO export_log (seller_id, from_date, to_date) VALUES (?, ?, ?) RETURNING id").params(sellerId, from, to).query(Long.class).single();
    }

    java.util.List<ExportController.ExportEntry> history(long sellerId) {
        return jdbc.sql("SELECT from_date AS \"from\", to_date AS \"to\", exported_at, rows_sent FROM export_log WHERE seller_id = ? ORDER BY id DESC")
                .param(sellerId).query(ExportController.ExportEntry.class).list();
    }

    /**
     * Writes the seller's orders, oldest first, as rows arrive from the database: PostgreSQL hands them over 1,000 at a
     * time through a cursor (fetch size, in a transaction), and each row is written and forgotten. Memory stays the
     * same for ten orders or a year of them. The days are IST days.
     */
    void write(long logId, long sellerId, LocalDate from, LocalDate to, String status, OutputStream out) throws IOException {
        int[] rows = {0};
        BufferedWriter w = new BufferedWriter(new OutputStreamWriter(out, StandardCharsets.UTF_8));
        w.write('\uFEFF');   // a byte order mark, so Excel reads the file as UTF-8 (Hindi product names)
        w.write(HEADER);
        w.write("\r\n");
        try {
            readOnly.executeWithoutResult(s -> jdbc.sql("""
                            SELECT order_ref, placed_at, product_name, quantity, amount_paise, buyer_city, status FROM orders
                            WHERE seller_id = ? AND placed_at >= ? AND placed_at < ? AND (CAST(? AS text) IS NULL OR status = ?) ORDER BY placed_at, id""")
                    .params(sellerId, start(from), start(to.plusDays(1)), status, status)
                    .query(rs -> {
                        try {
                            w.write(Csv.text(rs.getString(1)) + "," + rs.getObject(2, OffsetDateTime.class).atZoneSameInstant(IST).format(TIME) + ","
                                    + Csv.text(rs.getString(3)) + "," + rs.getInt(4) + "," + BigDecimal.valueOf(rs.getLong(5), 2).toPlainString() + ","
                                    + Csv.text(rs.getString(6)) + "," + rs.getString(7) + "\r\n");
                            rows[0]++;
                        } catch (IOException e) {
                            throw new UncheckedIOException(e);   // the client went away: stop reading
                        }
                    }));
        } catch (UncheckedIOException e) {
            throw e.getCause();
        }
        w.flush();
        jdbc.sql("UPDATE export_log SET rows_sent = ? WHERE id = ?").params(rows[0], logId).update();   // only after the last row
    }

    private static OffsetDateTime start(LocalDate istDay) {
        return istDay.atStartOfDay(IST).toOffsetDateTime();
    }
}
