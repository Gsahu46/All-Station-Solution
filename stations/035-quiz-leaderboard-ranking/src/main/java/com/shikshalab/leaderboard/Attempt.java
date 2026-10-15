package com.shikshalab.leaderboard;

/** A student's attempt at a quiz: one per student per quiz (demo rule). seconds is how long they took. */
record Attempt(String studentId, String name, int score, int seconds) {
}
