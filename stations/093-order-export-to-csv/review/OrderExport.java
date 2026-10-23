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
import java.util.List;

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
    void log(long sellerId, LocalDate from, LocalDate to) {
        jdbc.sql("INSERT INTO export_log (seller_id, from_date, to_date) VALUES (?, ?, ?)").params(sellerId, from, to).update();
    }

    /**
     * Writes the seller's orders, oldest first, as rows arrive from the database: PostgreSQL hands them over 1,000 at a
     * time through a cursor (fetch size, in a transaction), and each row is written and forgotten. Memory stays the
     * same for ten orders or a year of them. The days are IST days.
     */
    void write(long sellerId, LocalDate from, LocalDate to, OutputStream out) throws IOException {
        BufferedWriter w = new BufferedWriter(new OutputStreamWriter(out, StandardCharsets.UTF_8));
        w.write('\uFEFF');   // a byte order mark, so Excel reads the file as UTF-8 (Hindi product names)
        w.write(HEADER);
        w.write("\r\n");
        // Read the rows first, then write: the connection goes back to the pool sooner, and the code is simpler.
        record Row(String ref, OffsetDateTime at, String product, int quantity, long paise, String city, String status) {
        }
        List<Row> rows = jdbc.sql("""
                        SELECT order_ref AS ref, placed_at AS at, product_name AS product, quantity, amount_paise AS paise, buyer_city AS city, status FROM orders
                        WHERE seller_id = ? AND placed_at >= ? AND placed_at < ? ORDER BY placed_at, id""")
                .params(sellerId, start(from), start(to.plusDays(1))).query(Row.class).list();
        for (Row r : rows) {
            w.write(Csv.text(r.ref()) + "," + r.at().atZoneSameInstant(IST).format(TIME) + "," + Csv.text(r.product()) + "," + r.quantity() + ","
                    + BigDecimal.valueOf(r.paise(), 2).toPlainString() + "," + Csv.text(r.city()) + "," + r.status() + "\r\n");
        }
        w.flush();
    }

    private static OffsetDateTime start(LocalDate istDay) {
        return istDay.atStartOfDay(IST).toOffsetDateTime();
    }
}
