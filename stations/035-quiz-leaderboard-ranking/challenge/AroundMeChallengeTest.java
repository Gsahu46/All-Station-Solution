package com.shikshalab.leaderboard;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.groups.Tuple.tuple;

/**
 * Challenge 1: students far down the board want to see who is near them. Add Leaderboard.around(quizId, studentId, k):
 * up to k rows above and k rows below the student, in board order, with ranks from the whole board (not from the
 * window). Near the top or bottom, the window is just shorter.
 */
class AroundMeChallengeTest {

    static final Leaderboard BOARD = new Leaderboard(new Quizzes());

    @Test
    void twoAboveAndTwoBelowWithTheirRealRanks() {
        assertThat(BOARD.around(3, "S-1007", 2)).extracting(Leaderboard.Row::name, Leaderboard.Row::rank)
                .containsExactly(tuple("Meera", 3), tuple("Rohan", 5), tuple("Vihaan", 6), tuple("Ananya", 6), tuple("Ishita", 8));
    }

    @Test
    void atTheTopThereIsNothingAbove() {
        assertThat(BOARD.around(3, "S-1001", 2)).extracting(Leaderboard.Row::name).containsExactly("Aarav", "Diya", "Kabir");
        assertThat(BOARD.around(3, "S-1012", 1)).extracting(Leaderboard.Row::name, Leaderboard.Row::rank)
                .containsExactly(tuple("Reyansh", 10), tuple("Tara", 12));
    }
}
