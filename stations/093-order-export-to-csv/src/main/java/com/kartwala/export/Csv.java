package com.kartwala.export;

/** One CSV cell, safe for spreadsheets. */
final class Csv {

    private Csv() {
    }

    /**
     * Text that starts with = + - @ (or a tab or carriage return) is a formula to Excel, Sheets and LibreOffice:
     * a product named =HYPERLINK(...) would run when the seller opens the file. Such text gets a leading ' so it
     * stays text (the OWASP advice for CSV injection). Then RFC 4180 quoting: a cell with a comma, quote or line
     * break is quoted, and quotes inside are doubled.
     */
    static String text(String value) {
        String v = value;
        if (!v.isEmpty() && "=+-@\t\r".indexOf(v.charAt(0)) >= 0) {
            v = "'" + v;
        }
        if (v.contains(",") || v.contains("\"") || v.contains("\n") || v.contains("\r")) {
            v = "\"" + v.replace("\"", "\"\"") + "\"";
        }
        return v;
    }
}
