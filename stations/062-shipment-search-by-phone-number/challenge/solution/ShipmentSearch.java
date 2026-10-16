package com.dakroute.shipments;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.TreeMap;

@Service
class ShipmentSearch {

    record Shipment(String awb, LocalDate bookedOn, String status) {
    }

    record Result(String phone, LocalDate from, LocalDate to, List<Shipment> shipments) {
    }

    /** Support reads the newest first; a customer with more is asked to narrow the dates. */
    static final int LIMIT = 50;

    /** The column is compared as stored, so shipments_phone_booked_on answers it: phone by equality, then the date range. */
    static final String SQL = """
            SELECT awb, booked_on, status FROM shipments
            WHERE phone = :phone AND booked_on BETWEEN :from AND :to
            ORDER BY booked_on DESC, id DESC LIMIT :limit""";

    private final JdbcClient jdbc;

    ShipmentSearch(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    /** Challenge 1: the unique constraint's index finds one number. */
    Optional<Shipment> byAwb(String awb) {
        return jdbc.sql("SELECT awb, booked_on, status FROM shipments WHERE awb = ?").param(awb).query(Shipment.class).optional();
    }

    /** Challenge 2: answered by an index-only scan of shipments_phone_booked_on, which now includes status. */
    Map<String, Long> summary(String phone, LocalDate from, LocalDate to) {
        Map<String, Long> counts = new TreeMap<>();
        jdbc.sql("SELECT status, count(*) AS n FROM shipments WHERE phone = ? AND booked_on BETWEEN ? AND ? GROUP BY status")
                .params(phone, from, to).query((rs, i) -> counts.put(rs.getString("status"), rs.getLong("n"))).list();
        return counts;
    }

    Result search(String phone, LocalDate from, LocalDate to) {
        List<Shipment> shipments = jdbc.sql(SQL).param("phone", phone).param("from", from).param("to", to).param("limit", LIMIT)
                .query(Shipment.class).list();
        return new Result(phone, from, to, shipments);
    }
}
