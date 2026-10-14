package com.tijori.statementimport;

import java.util.ArrayList;
import java.util.List;

/** Splits one CSV line (RFC 4180 style): commas separate fields, double quotes wrap fields that contain commas. */
final class CsvLine {

    private CsvLine() {
    }

    static List<String> split(String line) throws LineException {
        List<String> fields = new ArrayList<>();
        StringBuilder field = new StringBuilder();
        boolean quoted = false;
        for (int i = 0; i < line.length(); i++) {
            char c = line.charAt(i);
            if (quoted) {
                if (c == '"' && i + 1 < line.length() && line.charAt(i + 1) == '"') {
                    field.append('"');   // "" inside quotes is one quote
                    i++;
                } else if (c == '"') {
                    quoted = false;
                } else {
                    field.append(c);
                }
            } else if (c == '"') {
                quoted = true;
            } else if (c == ',') {
                fields.add(field.toString().strip());
                field.setLength(0);
            } else {
                field.append(c);
            }
        }
        if (quoted) {
            throw new LineException("line", line, "a quote is opened and never closed");
        }
        fields.add(field.toString().strip());
        return fields;
    }
}
