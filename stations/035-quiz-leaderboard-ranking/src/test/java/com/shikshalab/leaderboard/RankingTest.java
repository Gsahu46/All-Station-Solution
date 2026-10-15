package com.shikshalab.leaderboard;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.groups.Tuple.tuple;

/** Ranking rules without Spring. */
class RankingTest {

    static final Quizzes QUIZZES = new Quizzes();
    static final Leaderboard BOARD = new Leaderboard(QUIZZES);

    @Test
    void competitionAndDenseRanksOnTheHandCheckedQuiz() {
        assertThat(BOARD.top(3, 12).rows()).extracting(Leaderboard.Row::name, Leaderboard.Row::rank, Leaderboard.Row::denseRank)
                .containsExactly(tuple("Aarav", 1, 1), tuple("Diya", 2, 2), tuple("Kabir", 3, 3), tuple("Meera", 3, 3),
                        tuple("Rohan", 5, 4), tuple("Vihaan", 6, 5), tuple("Ananya", 6, 5), tuple("Ishita", 8, 6),
                        tuple("Arjun", 9, 7), tuple("Saanvi", 10, 8), tuple("Reyansh", 10, 8), tuple("Tara", 12, 9));
    }

    @Test
    void equalScoreAndEqualTimeAreOrderedByStudentIdAndShareTheRank() {
        List<Attempt> twins = List.of(new Attempt("S-0002", "B", 50, 100), new Attempt("S-0001", "A", 50, 100), new Attempt("S-0003", "C", 90, 500));
        List<Attempt> best = Leaderboard.topN(twins, 3);
        assertThat(best).extracting(Attempt::studentId).containsExactly("S-0003", "S-0001", "S-0002");
    }

    @Test
    void reversingTheWholeChainWouldPutTheSlowerFirst() {
        // A common slip: reversed() at the end reverses every key, so on equal scores the slower student wins.
        Comparator<Attempt> wrong = Comparator.comparingInt(Attempt::score).thenComparingInt(Attempt::seconds).reversed();
        Attempt fast = new Attempt("S-0001", "fast", 70, 240);
        Attempt slow = new Attempt("S-0002", "slow", 70, 270);
        assertThat(wrong.compare(fast, slow)).isPositive();              // fast sorts after slow
        assertThat(Leaderboard.ORDER.compare(fast, slow)).isNegative();  // the real order: fast first
    }

    @ParameterizedTest
    @ValueSource(ints = {1, 10, 100, 1_999, 2_000, 2_500})
    void theHeapGivesTheSameTopNAsSortingEveryone(int n) {
        List<Attempt> all = new ArrayList<>(QUIZZES.find(7).orElseThrow().attempts());
        all.sort(Leaderboard.ORDER);
        assertThat(Leaderboard.topN(QUIZZES.find(7).orElseThrow().attempts(), n)).isEqualTo(all.subList(0, Math.min(n, all.size())));
    }

    @Test
    void myPlaceMatchesTheBoardForEveryStudent() {
        for (Leaderboard.Row row : BOARD.top(7, 100).rows()) {
            var me = BOARD.me(7, row.studentId());
            assertThat(me.rank()).as(row.studentId()).isEqualTo(row.rank());
            assertThat(me.denseRank()).as(row.studentId()).isEqualTo(row.denseRank());
        }
    }

    @Test
    void theCutoffCountIsEveryoneTiedWithTheLastRowWhoDidNotFit() {
        var board = BOARD.top(7, 100);
        int lastScore = board.rows().getLast().score();
        long tiedOverall = QUIZZES.find(7).orElseThrow().attempts().stream().filter(a -> a.score() == lastScore).count();
        long tiedShown = board.rows().stream().filter(r -> r.score() == lastScore).count();
        assertThat(board.moreTiedAtCutoff()).isEqualTo(tiedOverall - tiedShown).isPositive();
    }
}
