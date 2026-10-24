package com.bimaly.integration;

import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Reads a bank's policy file. A file that cannot be read at all is a {@link BadFileException}; a bad line is only
 * rejected, with its reason, and the other lines go on.
 * Demo rules: KOSHBANK-20261024.csv; UTF-8; the header below; five columns with no commas or quotes inside them;
 * at most 10,000 lines.
 */
final class PolicyFile {

    static final String HEADER = "reference,customer_name,date_of_birth,product_code,sum_insured_paise";
    static final int MAX_LINES = 10_000;
    private static final Pattern NAME = Pattern.compile("([A-Za-z]{3,12})-(\\d{8})\\.csv");
    private static final Pattern REFERENCE = Pattern.compile("[A-Za-z0-9-]{4,20}");
    private static final Pattern PRODUCT = Pattern.compile("[A-Za-z0-9]{3,10}");

    record Rejected(int line, String reference, String reason) {
    }

    record Parsed(int lines, List<PolicyRequest> accepted, List<Rejected> rejected) {
    }

    static final class BadFileException extends RuntimeException {
        BadFileException(String message) {
            super(message);
        }
    }

    private PolicyFile() {
    }

    static Parsed parse(String fileName, byte[] content) {
        Matcher name = NAME.matcher(fileName);
        if (!name.matches()) {
            throw new BadFileException("The file name " + fileName + " is not BANK-YYYYMMDD.csv.");
        }
        String bank = name.group(1).toUpperCase(Locale.ROOT);
        List<String> lines = utf8(content).lines().toList();
        if (lines.isEmpty() || !lines.getFirst().strip().equalsIgnoreCase(HEADER)) {
            throw new BadFileException("The first line is not the header " + HEADER + ".");
        }
        if (lines.size() - 1 > MAX_LINES) {
            throw new BadFileException("The file has " + (lines.size() - 1) + " lines; the limit is " + MAX_LINES + ".");
        }
        List<PolicyRequest> accepted = new ArrayList<>();
        List<Rejected> rejected = new ArrayList<>();
        Map<String, Integer> seen = new HashMap<>();
        int count = 0;
        for (int i = 1; i < lines.size(); i++) {
            if (lines.get(i).isBlank()) {
                continue;
            }
            count++;
            int lineNo = i + 1;
            String[] f = lines.get(i).split(",", -1);
            String ref = f[0].strip().toUpperCase(Locale.ROOT);
            String reason = f.length != 5 ? "expected 5 columns, found " + f.length : check(f);
            if (reason == null && seen.containsKey(ref)) {
                reason = "reference " + ref + " already appears on line " + seen.get(ref);
            }
            if (reason != null) {
                rejected.add(new Rejected(lineNo, ref, reason));
                continue;
            }
            seen.put(ref, lineNo);
            accepted.add(new PolicyRequest(bank, ref, f[1].strip(), LocalDate.parse(f[2].strip()),
                    f[3].strip().toUpperCase(Locale.ROOT), Long.parseLong(f[4].strip())));
        }
        if (count == 0) {
            throw new BadFileException("The file has a header but no policies.");
        }
        return new Parsed(count, accepted, rejected);
    }

    /** Why a five-column line is wrong, or null. */
    private static String check(String[] f) {
        if (!REFERENCE.matcher(f[0].strip()).matches()) {
            return "the reference must be 4 to 20 letters, digits or dashes";
        }
        String customer = f[1].strip();
        if (customer.isEmpty() || customer.length() > 100) {
            return "the customer name must be 1 to 100 characters";
        }
        try {
            if (!LocalDate.parse(f[2].strip()).isBefore(LocalDate.now())) {
                return "the date of birth must be in the past";
            }
        } catch (DateTimeParseException e) {
            return "the date of birth must be YYYY-MM-DD";
        }
        if (!PRODUCT.matcher(f[3].strip()).matches()) {
            return "the product code must be 3 to 10 letters or digits";
        }
        try {
            long sum = Long.parseLong(f[4].strip());
            if (sum <= 0 || sum > 1_000_000_000_000L) {
                return "the sum insured must be 1 to 1000000000000 paise";
            }
        } catch (NumberFormatException e) {
            return "the sum insured must be a whole number of paise";
        }
        return null;
    }

    private static String utf8(byte[] content) {
        try {
            return StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT)
                    .decode(ByteBuffer.wrap(content)).toString();
        } catch (CharacterCodingException e) {
            throw new BadFileException("The file is not UTF-8.");
        }
    }
}
