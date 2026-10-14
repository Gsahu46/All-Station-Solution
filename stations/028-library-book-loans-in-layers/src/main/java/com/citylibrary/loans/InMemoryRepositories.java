package com.citylibrary.loans;

import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

/**
 * In-memory implementations of the three repositories, with demo data: Asha has nothing out, Ravi owes a fine,
 * Meera has 3 books out. Replace them with database-backed ones and nothing above them changes.
 */
final class InMemoryRepositories {

    private InMemoryRepositories() {
    }

    @Repository
    static class Members implements Repositories.MemberRepository {
        private final Map<String, Model.Member> byId = new ConcurrentHashMap<>();

        Members() {
            reset();
        }

        void reset() {
            byId.clear();
            for (Model.Member m : List.of(new Model.Member("m-1", "Asha Rao", "CL-0001", 0),
                    new Model.Member("m-2", "Ravi Kumar", "CL-0002", 2_000),
                    new Model.Member("m-3", "Meera Iyer", "CL-0003", 0))) {
                byId.put(m.id(), m);
            }
        }

        @Override
        public Optional<Model.Member> findById(String id) {
            return Optional.ofNullable(byId.get(id));
        }

        @Override
        public Optional<Model.Member> findByCardNumber(String cardNumber) {
            return byId.values().stream().filter(m -> m.cardNumber().equals(cardNumber)).findFirst();
        }

        @Override
        public void save(Model.Member member) {
            byId.put(member.id(), member);
        }
    }

    @Repository
    static class Books implements Repositories.BookRepository {
        private final Map<String, Model.Book> byId = new ConcurrentHashMap<>();

        Books() {
            String[] titles = {"Malgudi Days", "Wings of Fire", "The God of Small Things", "Train to Pakistan", "Godaan",
                    "Gitanjali", "The Discovery of India", "Sea of Poppies"};
            for (int i = 1; i <= titles.length; i++) {
                byId.put("b-" + i, new Model.Book("b-" + i, titles[i - 1], "LIB" + (100000 + i)));
            }
        }

        @Override
        public Optional<Model.Book> findById(String id) {
            return Optional.ofNullable(byId.get(id));
        }

        @Override
        public Optional<Model.Book> findByBarcode(String barcode) {
            return byId.values().stream().filter(b -> b.barcode().equals(barcode)).findFirst();
        }
    }

    @Repository
    static class Loans implements Repositories.LoanRepository {
        private final Map<String, Model.Loan> byId = new ConcurrentHashMap<>();

        Loans() {
            reset();
        }

        void reset() {
            byId.clear();
            LocalDate borrowed = LocalDate.of(2026, 10, 1);
            for (int i = 6; i <= 8; i++) {
                byId.put("l-" + i, new Model.Loan("l-" + i, "m-3", "b-" + i, borrowed, borrowed.plusDays(14), null, 0));
            }
        }

        @Override
        public Optional<Model.Loan> findById(String id) {
            return Optional.ofNullable(byId.get(id));
        }

        @Override
        public List<Model.Loan> findByMember(String memberId) {
            return byId.values().stream().filter(l -> l.memberId().equals(memberId))
                    .sorted(Comparator.comparing(Model.Loan::borrowedOn).thenComparing(Model.Loan::id)).toList();
        }

        @Override
        public Optional<Model.Loan> findActiveByBook(String bookId) {
            return byId.values().stream().filter(l -> l.bookId().equals(bookId) && l.active()).findFirst();
        }

        @Override
        public void save(Model.Loan loan) {
            byId.put(loan.id(), loan);
        }
    }
}
