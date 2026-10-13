package com.seatsure.registrations;

import java.util.List;
import java.util.stream.Collectors;
import java.util.stream.Stream;

/** Challenge 2: registrations as CSV (RFC 4180: comma-separated, CRLF line ends, quotes doubled inside quoted fields). */
final class CsvExport {

    private CsvExport() {
    }

    static String of(List<Registration> rows) {
        StringBuilder csv = new StringBuilder("name,email,phone,tickets\r\n");
        for (Registration r : rows) {
            csv.append(Stream.of(r.name(), r.email(), r.phone() == null ? "" : r.phone(), String.valueOf(r.tickets()))
                    .map(CsvExport::field)
                    .collect(Collectors.joining(","))).append("\r\n");
        }
        return csv.toString();
    }

    /**
     * A spreadsheet runs a cell that starts with = + - or @ as a formula (OWASP "CSV injection"), so such text
     * gets a leading apostrophe. A field with a comma, quote or line break is wrapped in quotes, inner quotes doubled.
     */
    static String field(String value) {
        String v = !value.isEmpty() && "=+-@\t\r".indexOf(value.charAt(0)) >= 0 ? "'" + value : value;
        return v.matches("(?s).*[,\"\r\n].*") ? "\"" + v.replace("\"", "\"\"") + "\"" : v;
    }
}
