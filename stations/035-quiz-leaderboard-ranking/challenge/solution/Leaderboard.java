package com.shikshalab.leaderboard;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.stereotype.Service;
import org.springframework.web.ErrorResponseException;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.PriorityQueue;
import java.util.function.BinaryOperator;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * Ranks are by score only, so equal scores share a rank: competition ranking ("1, 2, 2, 4"), with the dense rank
 * ("1, 2, 2, 3") alongside. Inside a tie, rows are shown faster first, then by student id, so the order is the same
 * on every request. "Top N" is at most N rows; anyone tied with the last row who did not fit is counted, not shown.
 */
@Service
class Leaderboard {

    /** Higher score first; on equal scores, less time first; then student id, so no two rows compare equal. */
    static final Comparator<Attempt> ORDER = Comparator.comparingInt(Attempt::score).reversed()
            .thenComparingInt(Attempt::seconds)
            .thenComparing(Attempt::studentId);

    record Row(int rank, int denseRank, String studentId, String name, int score, int seconds) {
    }

    record Board(long quizId, String title, int participants, List<Row> rows, int moreTiedAtCutoff) {
    }

    record MyPlace(long quizId, String studentId, String name, int score, int seconds, int rank, int denseRank, int participants) {
    }

    private final Quizzes quizzes;

    Leaderboard(Quizzes quizzes) {
        this.quizzes = quizzes;
    }

    Board top(long quizId, int n) {
        Quiz quiz = quiz(quizId);
        List<Attempt> everyone = bestPerStudent(quiz.attempts());
        List<Attempt> best = topN(everyone, n);
        List<Row> rows = ranked(best);
        int more = 0;
        if (!best.isEmpty()) {
            int lastScore = best.getLast().score();
            more = (int) (everyone.stream().filter(a -> a.score() == lastScore).count() - best.stream().filter(a -> a.score() == lastScore).count());
        }
        return new Board(quiz.id(), quiz.title(), everyone.size(), rows, more);
    }

    /** Ranks for a list sorted by ORDER that starts at the top of the board. */
    static List<Row> ranked(List<Attempt> sorted) {
        List<Row> rows = new ArrayList<>(sorted.size());
        for (int i = 0; i < sorted.size(); i++) {
            Attempt a = sorted.get(i);
            Row previous = i == 0 ? null : rows.get(i - 1);
            boolean tied = previous != null && previous.score() == a.score();
            int rank = tied ? previous.rank() : i + 1;
            int dense = tied ? previous.denseRank() : (previous == null ? 1 : previous.denseRank() + 1);
            rows.add(new Row(rank, dense, a.studentId(), a.name(), a.score(), a.seconds()));
        }
        return rows;
    }

    /** Up to k rows either side of the student, ranked over the whole board. */
    List<Row> around(long quizId, String studentId, int k) {
        List<Attempt> everyone = new ArrayList<>(bestPerStudent(quiz(quizId).attempts()));
        everyone.sort(ORDER);
        List<Row> all = ranked(everyone);
        int i = 0;
        while (i < all.size() && !all.get(i).studentId().equals(studentId)) {
            i++;
        }
        if (i == all.size()) {
            throw problem(HttpStatus.NOT_FOUND, "No attempt", studentId + " has not attempted quiz " + quizId + ".");
        }
        return all.subList(Math.max(0, i - k), Math.min(all.size(), i + k + 1));
    }

    /** Each student's best attempt: highest score, then fastest. */
    static List<Attempt> bestPerStudent(List<Attempt> attempts) {
        return List.copyOf(attempts.stream()
                .collect(Collectors.toMap(Attempt::studentId, Function.identity(), BinaryOperator.minBy(ORDER)))
                .values());
    }

    /** The best n, sorted. A heap of at most n + 1 attempts: O(attempts × log n), and memory for n, not for everyone. */
    static List<Attempt> topN(List<Attempt> attempts, int n) {
        PriorityQueue<Attempt> heap = new PriorityQueue<>(ORDER.reversed());   // the worst of the best on top, to drop
        for (Attempt a : attempts) {
            heap.offer(a);
            if (heap.size() > n) {
                heap.poll();
            }
        }
        List<Attempt> best = new ArrayList<>(heap);
        best.sort(ORDER);
        return best;
    }

    MyPlace me(long quizId, String studentId) {
        Quiz quiz = quiz(quizId);
        List<Attempt> everyone = bestPerStudent(quiz.attempts());
        Attempt mine = everyone.stream().filter(a -> a.studentId().equals(studentId)).findFirst()
                .orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "No attempt", studentId + " has not attempted quiz " + quizId + "."));
        int rank = 1 + (int) everyone.stream().filter(a -> a.score() > mine.score()).count();
        int dense = 1 + (int) everyone.stream().mapToInt(Attempt::score).filter(s -> s > mine.score()).distinct().count();
        return new MyPlace(quizId, studentId, mine.name(), mine.score(), mine.seconds(), rank, dense, everyone.size());
    }

    private Quiz quiz(long quizId) {
        return quizzes.find(quizId).orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "Quiz not found", "No quiz " + quizId + "."));
    }

    private static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setTitle(title);
        return new ErrorResponseException(status, p, null);
    }
}
