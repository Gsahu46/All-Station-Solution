package com.citylibrary.loans;

import java.time.LocalDate;

/** The library's records. Plain data: the rules about them live in LoanService. */
final class Model {

    private Model() {
    }

    record Member(String id, String name, String cardNumber, long unpaidFinePaise) {
        Member withFine(long more) {
            return new Member(id, name, cardNumber, unpaidFinePaise + more);
        }

        /** Challenge 1. */
        Member withPayment(long paise) {
            return new Member(id, name, cardNumber, unpaidFinePaise - paise);
        }
    }

    record Book(String id, String title, String barcode) {
    }

    /** Challenge 2 adds renewals; the 7-value constructor stays for code that does not know about them. */
    record Loan(String id, String memberId, String bookId, LocalDate borrowedOn, LocalDate dueOn, LocalDate returnedOn,
                long finePaise, int renewals) {
        Loan(String id, String memberId, String bookId, LocalDate borrowedOn, LocalDate dueOn, LocalDate returnedOn, long finePaise) {
            this(id, memberId, bookId, borrowedOn, dueOn, returnedOn, finePaise, 0);
        }

        boolean active() {
            return returnedOn == null;
        }
    }
}
