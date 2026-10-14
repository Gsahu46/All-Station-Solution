package com.tijori.statementimport;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.time.format.ResolverStyle;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * Reads the statement CSV line by line. A bad line becomes an error with its line number; the other lines still
 * count. Columns are found by name in the header row, in any order (challenge 2); each line's balance must follow
 * from the line before (challenge 1).
 */
final class StatementParser {

    static final List<String> HEADER = List.of("date", "description", "debit", "credit", "balance");

    /** Challenge 2: other names banks use for the same columns. */
    static final Map<String, List<String>> ALIASES = Map.of(
            "date", List.of("txn date", "transaction date", "value date"),
            "description", List.of("narration", "particulars"),
            "debit", List.of("withdrawal amt", "withdrawal"),
            "credit", List.of("deposit amt", "deposit"),
            "balance", List.of("closing balance"));

    /** Where each of the five columns is in this file. */
    record Columns(int date, int description, int debit, int credit, int balance, int count) {
    }
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
        Columns columns = columns(lines.getFirst());
        List<Transaction> transactions = new ArrayList<>();
        List<LineError> errors = new ArrayList<>();
        Long previousBalance = null;   // null after a line that could not be read: nothing reliable to compare with
        for (int i = 1; i < lines.size(); i++) {
            int lineNumber = i + 1;   // as a spreadsheet shows it: the header is line 1
            if (lines.get(i).isBlank()) {
                continue;
            }
            try {
                Transaction t = parseLine(lineNumber, lines.get(i), columns);
                Long expected = previousBalance;
                previousBalance = t.balancePaise();   // the next line follows the stated balance, so one slip is one error
                if (expected != null) {
                    long should = expected - t.debitPaise() + t.creditPaise();
                    if (should != t.balancePaise()) {
                        throw new LineException("balance", rupees(t.balancePaise()), "should be " + rupees(should)
                                + " (" + rupees(expected) + " - " + rupees(t.debitPaise()) + " + " + rupees(t.creditPaise()) + ")");
                    }
                }
                transactions.add(t);
            } catch (LineException e) {
                errors.add(new LineError(lineNumber, e.field, shorten(e.value), e.getMessage()));
                previousBalance = null;
            }
        }
        String status = errors.isEmpty() ? "COMPLETE" : transactions.isEmpty() ? "REJECTED" : "PARTIAL";
        return new Result(status, lines.size() - 1, transactions, errors.size(),
                errors.subList(0, Math.min(errors.size(), MAX_ERRORS_SHOWN)));
    }

    /** Challenge 2: each column's position, by its name or an alias, case-insensitive. Extra columns are ignored. */
    static Columns columns(String header) {
        List<String> names;
        try {
            names = CsvLine.split(header.replace("\uFEFF", "")).stream().map(n -> n.toLowerCase(Locale.ROOT)).toList();
        } catch (LineException e) {
            throw new FileProblem("The header row cannot be read: " + e.getMessage() + ".");
        }
        int[] at = new int[HEADER.size()];
        for (int c = 0; c < HEADER.size(); c++) {
            String column = HEADER.get(c);
            at[c] = names.indexOf(column);
            for (String alias : ALIASES.get(column)) {
                at[c] = at[c] >= 0 ? at[c] : names.indexOf(alias);
            }
            if (at[c] < 0) {
                throw new FileProblem("The header has no " + column + " column (also accepted: " + String.join(", ", ALIASES.get(column)) + ").");
            }
        }
        return new Columns(at[0], at[1], at[2], at[3], at[4], names.size());
    }

    static Transaction parseLine(int lineNumber, String line, Columns c) throws LineException {
        List<String> f = CsvLine.split(line);
        if (f.size() != c.count()) {
            throw new LineException("line", line, "has " + f.size() + " fields; expected " + c.count());
        }
        LocalDate date = date(f.get(c.date()));
        String description = f.get(c.description());
        if (description.isEmpty()) {
            throw new LineException("description", "", "is empty");
        }
        long debit = paise("debit", f.get(c.debit()));
        long credit = paise("credit", f.get(c.credit()));
        if ((debit == 0) == (credit == 0)) {
            throw new LineException("debit", f.get(c.debit()) + " / " + f.get(c.credit()), "exactly one of debit and credit must have an amount");
        }
        return new Transaction(lineNumber, date, description, debit, credit, paise("balance", f.get(c.balance())));
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

    private static String rupees(long paise) {
        return BigDecimal.valueOf(paise, 2).toPlainString();
    }

    private static String shorten(String value) {
        return value.length() <= 40 ? value : value.substring(0, 40) + "…";
    }
}
