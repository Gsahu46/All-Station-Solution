package com.citylibrary.loans;

import org.springframework.stereotype.Service;

import java.time.Clock;
import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.UUID;

/**
 * Every loan rule, in one place. The web API and the kiosk both call this; neither has a rule of its own.
 * Rules (demo rules for this library): at most 3 books out per member; no new loan while a fine is unpaid; a book is
 * lent to one member at a time; 14 days per loan; Rs 5 a day for each late day.
 */
@Service
class LoanService {

    static final int MAX_BOOKS = 3;
    static final int LOAN_DAYS = 14;
    static final long FINE_PER_DAY_PAISE = 500;

    enum Reason { LIMIT_REACHED, UNPAID_FINE, BOOK_ON_LOAN, ALREADY_RETURNED }

    /** A rule said no. Carries why, so every entry point can explain it the same way. */
    static final class Refused extends RuntimeException {
        final Reason reason;

        Refused(Reason reason, String message) {
            super(message);
            this.reason = reason;
        }
    }

    static final class NotFound extends RuntimeException {
        NotFound(String message) {
            super(message);
        }
    }

    private final Repositories.MemberRepository members;
    private final Repositories.BookRepository books;
    private final Repositories.LoanRepository loans;
    private final Clock clock;

    /** Constructor injection: every dependency is visible, final, and easy to replace in a unit test. */
    LoanService(Repositories.MemberRepository members, Repositories.BookRepository books, Repositories.LoanRepository loans, Clock clock) {
        this.members = members;
        this.books = books;
        this.loans = loans;
        this.clock = clock;
    }

    /** synchronized: check-then-save across repositories must not interleave. Safe while one instance runs. */
    synchronized Model.Loan borrow(String memberId, String bookId) {
        Model.Member member = members.findById(memberId).orElseThrow(() -> new NotFound("No member " + memberId + "."));
        Model.Book book = books.findById(bookId).orElseThrow(() -> new NotFound("No book " + bookId + "."));
        if (member.unpaidFinePaise() > 0) {
            throw new Refused(Reason.UNPAID_FINE, member.name() + " has an unpaid fine of Rs " + rupees(member.unpaidFinePaise()) + ".");
        }
        long out = loans.findByMember(memberId).stream().filter(Model.Loan::active).count();
        if (out >= MAX_BOOKS) {
            throw new Refused(Reason.LIMIT_REACHED, member.name() + " already has " + out + " books out; the limit is " + MAX_BOOKS + ".");
        }
        if (loans.findActiveByBook(bookId).isPresent()) {
            throw new Refused(Reason.BOOK_ON_LOAN, "\"" + book.title() + "\" is already on loan.");
        }
        LocalDate today = LocalDate.now(clock);
        Model.Loan loan = new Model.Loan("l-" + UUID.randomUUID().toString().substring(0, 8), memberId, bookId, today,
                today.plusDays(LOAN_DAYS), null, 0);
        loans.save(loan);
        return loan;
    }

    /** The kiosk knows a library card and a barcode, not ids. Same rules, through the same method. */
    Model.Loan borrowAtKiosk(String cardNumber, String barcode) {
        Model.Member member = members.findByCardNumber(cardNumber).orElseThrow(() -> new NotFound("No member with card " + cardNumber + "."));
        Model.Book book = books.findByBarcode(barcode).orElseThrow(() -> new NotFound("No book with barcode " + barcode + "."));
        return borrow(member.id(), book.id());
    }

    synchronized Model.Loan giveBack(String loanId) {
        Model.Loan loan = loans.findById(loanId).orElseThrow(() -> new NotFound("No loan " + loanId + "."));
        if (!loan.active()) {
            throw new Refused(Reason.ALREADY_RETURNED, "Loan " + loanId + " was returned on " + loan.returnedOn() + ".");
        }
        LocalDate today = LocalDate.now(clock);
        long lateDays = Math.max(0, ChronoUnit.DAYS.between(loan.dueOn(), today));
        long fine = lateDays * FINE_PER_DAY_PAISE;
        Model.Loan returned = new Model.Loan(loan.id(), loan.memberId(), loan.bookId(), loan.borrowedOn(), loan.dueOn(), today, fine);
        loans.save(returned);
        if (fine > 0) {
            members.findById(loan.memberId()).ifPresent(m -> members.save(m.withFine(fine)));
        }
        return returned;
    }

    List<Model.Loan> loansOf(String memberId) {
        members.findById(memberId).orElseThrow(() -> new NotFound("No member " + memberId + "."));
        return loans.findByMember(memberId);
    }

    private static String rupees(long paise) {
        return paise / 100 + "." + String.format("%02d", paise % 100);
    }
}
