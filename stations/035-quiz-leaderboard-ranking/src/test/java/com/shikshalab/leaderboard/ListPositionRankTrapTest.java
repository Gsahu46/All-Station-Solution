package com.shikshalab.leaderboard;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/** The first test written for this station: both complaints, reproduced on quiz 3, and the fix. */
class ListPositionRankTrapTest {

    @Test
    void rankingByPositionGivesEqualScoresDifferentRanks() {
        var old = OldLeaderboard.byPosition(Quizzes.ALGEBRA_SPRINT.attempts());
        assertThat(old.get(2).score()).isEqualTo(old.get(3).score()).isEqualTo(88);   // Kabir and Meera, both 88
        assertThat(old.get(2).rank()).isEqualTo(3);
        assertThat(old.get(3).rank()).isEqualTo(4);
    }

    @Test
    void theQuickFixShowsElevenNamesInTheTopTen() {
        assertThat(OldLeaderboard.quickFixTop(Quizzes.ALGEBRA_SPRINT.attempts(), 10)).hasSize(11);   // two students tied at 10th
    }

    @Test
    void theFixSharesRanksAndShowsAtMostTenCountingTheRest() {
        var board = new Leaderboard(new Quizzes()).top(3, 10);
        assertThat(board.rows()).hasSize(10);
        assertThat(board.rows().get(2).rank()).isEqualTo(board.rows().get(3).rank()).isEqualTo(3);
        assertThat(board.rows().getLast().name()).isEqualTo("Saanvi");   // 70 in 240 s, faster than Reyansh's 70 in 270 s
        assertThat(board.moreTiedAtCutoff()).isEqualTo(1);
    }
}
