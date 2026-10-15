package com.shikshalab.leaderboard;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/** The leaderboard before the fix, kept only in tests: first by list position, then the quick fix. */
final class OldLeaderboard {

    record OldRow(int rank, String name, int score) {
    }

    private OldLeaderboard() {
    }

    /** Version 1: the rank is the position in the sorted list. */
    static List<OldRow> byPosition(List<Attempt> attempts) {
        List<Attempt> sorted = new ArrayList<>(attempts);
        sorted.sort(Comparator.comparingInt(Attempt::score).reversed());
        List<OldRow> rows = new ArrayList<>();
        for (int i = 0; i < sorted.size(); i++) {
            rows.add(new OldRow(i + 1, sorted.get(i).name(), sorted.get(i).score()));
        }
        return rows;
    }

    /** Version 2, the quick fix: equal scores share a rank, and "top 10" became "rank 10 or better". */
    static List<OldRow> quickFixTop(List<Attempt> attempts, int top) {
        List<OldRow> positions = byPosition(attempts);
        List<OldRow> rows = new ArrayList<>();
        for (int i = 0; i < positions.size(); i++) {
            OldRow r = positions.get(i);
            int rank = i > 0 && positions.get(i - 1).score() == r.score() ? rows.get(i - 1).rank() : i + 1;
            rows.add(new OldRow(rank, r.name(), r.score()));
        }
        return rows.stream().filter(r -> r.rank() <= top).toList();
    }
}
