package com.shikshalab.leaderboard;

import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Random;

/**
 * Demo quizzes. Quiz 3 is small enough to check by hand: ties at rank 3, at rank 6 and at rank 10. Quiz 7 has 2,000
 * generated attempts (fixed seed), for the top-N code to work on something larger.
 */
@Component
class Quizzes {

    static final Quiz ALGEBRA_SPRINT = new Quiz(3, "Algebra sprint", 100, List.of(
            new Attempt("S-1001", "Aarav", 95, 300),
            new Attempt("S-1002", "Diya", 92, 280),
            new Attempt("S-1003", "Kabir", 88, 250),
            new Attempt("S-1004", "Meera", 88, 310),
            new Attempt("S-1005", "Rohan", 85, 200),
            new Attempt("S-1006", "Ananya", 80, 400),
            new Attempt("S-1007", "Vihaan", 80, 260),
            new Attempt("S-1008", "Ishita", 78, 330),
            new Attempt("S-1009", "Arjun", 75, 290),
            new Attempt("S-1010", "Saanvi", 70, 240),
            new Attempt("S-1011", "Reyansh", 70, 270),
            new Attempt("S-1012", "Tara", 60, 300)));

    private static final List<String> FIRST = List.of("Aditi", "Aryan", "Bhavya", "Dev", "Esha", "Farhan", "Gauri", "Harsh",
            "Inaaya", "Jai", "Kiara", "Laksh", "Myra", "Neel", "Ojas", "Pari", "Rudra", "Sia", "Tanish", "Zoya");

    private final Map<Long, Quiz> byId;

    Quizzes() {
        Random random = new Random(7);
        List<Attempt> attempts = new ArrayList<>();
        for (int i = 0; i < 2_000; i++) {
            attempts.add(new Attempt("S-%04d".formatted(2000 + i), FIRST.get(random.nextInt(FIRST.size())) + " " + (char) ('A' + random.nextInt(26)) + ".",
                    40 + random.nextInt(61), 120 + random.nextInt(481)));   // scores 40 to 100: plenty of ties
        }
        byId = Map.of(3L, ALGEBRA_SPRINT, 7L, new Quiz(7, "Fractions practice", 100, attempts));
    }

    Optional<Quiz> find(long id) {
        return Optional.ofNullable(byId.get(id));
    }
}
