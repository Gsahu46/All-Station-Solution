package com.shikshalab.leaderboard;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Pattern;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Locale;

@RestController
class LeaderboardController {

    private final Leaderboard leaderboard;

    LeaderboardController(Leaderboard leaderboard) {
        this.leaderboard = leaderboard;
    }

    @GetMapping("/quizzes/{id}/leaderboard")
    Leaderboard.Board top(@PathVariable long id, @RequestParam(defaultValue = "10") @Min(1) @Max(100) int top) {
        return leaderboard.top(id, top);
    }

    /**
     * The caller's own place. X-Student-Id stands in for the signed-in student (demo): a real app takes it from the
     * login token, never from a header the client chooses.
     */
    @GetMapping("/quizzes/{id}/leaderboard/me")
    Leaderboard.MyPlace me(@PathVariable long id,
                           @RequestHeader("X-Student-Id") @Pattern(regexp = "(?i)S-\\d{4}", message = "must look like S-1003") String studentId) {
        return leaderboard.me(id, studentId.toUpperCase(Locale.ROOT));
    }
}
