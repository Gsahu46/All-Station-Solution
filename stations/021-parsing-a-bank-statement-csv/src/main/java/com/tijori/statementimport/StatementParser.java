package com.tijori.statementimport;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.time.format.ResolverStyle;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * Reads the statement CSV line by line. A bad line becomes an error with its line number; the other lines still
 * count. Columns: date, description, debit, credit, balance (the header row must name them, in this order).
 */
final class StatementParser {

    static final List<String> HEADER = List.of("date", "description", "debit", "credit", "balance");
    static final int MAX_LINES = 10_000;
    static final int MAX_ERRORS_SHOWN = 100;

    /**
     * STRICT, so 31/02/2026 is an error instead of quietly becoming 28 Feb. STRICT needs "uuuu" (proleptic year),
     * not "yyyy" (year of era), or every date fails.
     */
    static final List<DateTimeFormatter> DATE_FORMATS = List.of(
            DateTimeFormatter.ofPattern("dd/MM/uuuu").withResolverStyle(ResolverStyle.STRICT),
            DateTimeFormatter.ofPattern("dd-MM-uuuu").withResolverStyle(ResolverStyle.STRICT),
            DateTimeFormatter.ISO_LOCAL_DATE);

    record Transaction(int line, LocalDate date, String description, long debitPaise, long creditPaise, long balancePaise) {
    }

    record LineError(int line, String field, String value, String message) {
    }

    record Result(String status, int linesRead, List<Transaction> transactions, int errorCount, List<LineError> errors) {
    }

    /** Thrown for a problem with the file as a whole (no header, too long): unchecked, the controller maps it. */
    static final class FileProblem extends RuntimeException {
        FileProblem(String message) {
            super(message);
        }
    }

    private StatementParser() {
    }

    static Result parse(String csv) {
        List<String> lines = csv.lines().toList();   // not strip(): a leading blank line must not shift the line numbers
        if (lines.isEmpty() || lines.getFirst().isBlank()) {
            throw new FileProblem("The file is empty.");
        }
        if (lines.size() - 1 > MAX_LINES) {
            throw new FileProblem("The file has " + (lines.size() - 1) + " lines; at most " + MAX_LINES + " can be read at once.");
        }
        checkHeader(lines.getFirst());
        List<Transaction> transactions = new ArrayList<>();
        List<LineError> errors = new ArrayList<>();
        for (int i = 1; i < lines.size(); i++) {
            int lineNumber = i + 1;   // as a spreadsheet shows it: the header is line 1
            if (lines.get(i).isBlank()) {
                continue;
            }
            try {
                transactions.add(parseLine(lineNumber, lines.get(i)));
            } catch (LineException e) {
                errors.add(new LineError(lineNumber, e.field, shorten(e.value), e.getMessage()));
            }
        }
        String status = errors.isEmpty() ? "COMPLETE" : transactions.isEmpty() ? "REJECTED" : "PARTIAL";
        return new Result(status, lines.size() - 1, transactions, errors.size(),
                errors.subList(0, Math.min(errors.size(), MAX_ERRORS_SHOWN)));
    }

    private static void checkHeader(String header) {
        List<String> names;
        try {
            names = CsvLine.split(header.replace("﻿", "")).stream().map(n -> n.toLowerCase(Locale.ROOT)).toList();
        } catch (LineException e) {
            throw new FileProblem("The header row cannot be read: " + e.getMessage() + ".");
        }
        if (!names.equals(HEADER)) {
            // the line itself is not echoed back: without a header it may well be the customer's first transaction
            throw new FileProblem("The first line must be the header " + String.join(",", HEADER) + ".");
        }
    }

    static Transaction parseLine(int lineNumber, String line) throws LineException {
        List<String> f = CsvLine.split(line);
        if (f.size() != HEADER.size()) {
            throw new LineException("line", line, "has " + f.size() + " fields; expected " + HEADER.size());
        }
        LocalDate date = date(f.get(0));
        String description = f.get(1);
        if (description.isEmpty()) {
            throw new LineException("description", "", "is empty");
        }
        long debit = paise("debit", f.get(2));
        long credit = paise("credit", f.get(3));
        if ((debit == 0) == (credit == 0)) {
            throw new LineException("debit", f.get(2) + " / " + f.get(3), "exactly one of debit and credit must have an amount");
        }
        return new Transaction(lineNumber, date, description, debit, credit, paise("balance", f.get(4)));
    }

    static LocalDate date(String text) throws LineException {
        for (DateTimeFormatter format : DATE_FORMATS) {
            try {
                return LocalDate.parse(text, format);
            } catch (DateTimeParseException tryTheNextFormat) {
                // unchecked, so nothing forced us to catch it: we do, to try the next format
            }
        }
        throw new LineException("date", text, "is not a real date in dd/MM/yyyy, dd-MM-yyyy or yyyy-MM-dd");
    }

    /** "1,23,456.50" (Indian grouping) or "123456.5" to paise. Empty is zero. No minus signs: debit and credit say it. */
    static long paise(String field, String text) throws LineException {
        if (text.isEmpty()) {
            return 0;
        }
        String plain = text.replace(",", "");
        if (!plain.matches("\\d{1,13}(\\.\\d{1,2})?")) {
            throw new LineException(field, text, "is not an amount like 1,234.50");
        }
        return new BigDecimal(plain).movePointRight(2).longValueExact();
    }

    private static String shorten(String value) {
        return value.length() <= 40 ? value : value.substring(0, 40) + "…";
    }
}
