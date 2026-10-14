package com.citylibrary.loans;

import java.util.List;
import java.util.Optional;

/**
 * What the service needs from storage, as interfaces. The service never knows whether a map or a database sits
 * behind them; tests replace them with mocks.
 */
final class Repositories {

    private Repositories() {
    }

    interface MemberRepository {
        Optional<Model.Member> findById(String id);

        Optional<Model.Member> findByCardNumber(String cardNumber);

        void save(Model.Member member);
    }

    interface BookRepository {
        Optional<Model.Book> findById(String id);

        Optional<Model.Book> findByBarcode(String barcode);
    }

    interface LoanRepository {
        Optional<Model.Loan> findById(String id);

        List<Model.Loan> findByMember(String memberId);

        Optional<Model.Loan> findActiveByBook(String bookId);

        void save(Model.Loan loan);
    }
}
