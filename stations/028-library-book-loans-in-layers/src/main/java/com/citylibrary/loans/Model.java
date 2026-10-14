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
    }

    record Book(String id, String title, String barcode) {
    }

    record Loan(String id, String memberId, String bookId, LocalDate borrowedOn, LocalDate dueOn, LocalDate returnedOn,
                long finePaise) {
        boolean active() {
            return returnedOn == null;
        }
    }
}
