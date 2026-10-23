package com.kartwala.export;

/** One CSV cell, safe for spreadsheets. */
final class Csv {

    private Csv() {
    }

    /** RFC 4180 quoting; a cell that starts with = is quoted as well, so a spreadsheet keeps it as text. */
    static String text(String value) {
        if (value.startsWith("=") || value.contains(",") || value.contains("\"") || value.contains("\n") || value.contains("\r")) {
            return "\"" + value.replace("\"", "\"\"") + "\"";
        }
        return value;
    }
}
