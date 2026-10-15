package com.shikshalab.leaderboard;

import java.util.List;

record Quiz(long id, String title, int maxScore, List<Attempt> attempts) {

    Quiz {
        attempts = List.copyOf(attempts);
    }
}
