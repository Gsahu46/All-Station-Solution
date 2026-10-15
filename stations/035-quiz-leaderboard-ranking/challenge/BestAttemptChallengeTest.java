package com.shikshalab.leaderboard;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.groups.Tuple.tuple;

/**
 * Challenge 2: students may now try a quiz more than once. The board and "me" use each student's best attempt
 * (highest score, then fastest), and participants counts students, not attempts.
 */
class BestAttemptChallengeTest {

    static Quizzes quizzesWith(List<Attempt> attempts) {
        return new Quizzes() {
            @Override
            Optional<Quiz> find(long id) {
                return Optional.of(new Quiz(id, "Retry quiz", 100, attempts));
            }
        };
    }

    static final List<Attempt> ATTEMPTS = List.of(
            new Attempt("S-0001", "Asha", 70, 300),
            new Attempt("S-0001", "Asha", 90, 400),
            new Attempt("S-0001", "Asha", 90, 350),
            new Attempt("S-0002", "Bilal", 80, 200),
            new Attempt("S-0003", "Chitra", 90, 500));

    @Test
    void eachStudentAppearsOnceWithTheirBestAttempt() {
        var board = new Leaderboard(quizzesWith(ATTEMPTS)).top(9, 10);
        assertThat(board.participants()).isEqualTo(3);
        assertThat(board.rows()).extracting(Leaderboard.Row::name, Leaderboard.Row::score, Leaderboard.Row::seconds, Leaderboard.Row::rank)
                .containsExactly(tuple("Asha", 90, 350, 1), tuple("Chitra", 90, 500, 1), tuple("Bilal", 80, 200, 3));
    }

    @Test
    void myPlaceUsesMyBestAttemptToo() {
        var me = new Leaderboard(quizzesWith(ATTEMPTS)).me(9, "S-0001");
        assertThat(me).extracting(Leaderboard.MyPlace::score, Leaderboard.MyPlace::seconds, Leaderboard.MyPlace::rank, Leaderboard.MyPlace::participants)
                .containsExactly(90, 350, 1, 3);
    }
}
