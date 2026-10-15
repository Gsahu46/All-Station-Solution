package com.shikshalab.leaderboard;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.json.JsonCompareMode;
import org.springframework.test.web.servlet.MockMvc;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract on quiz 3, "Algebra sprint", whose ranks can be checked by hand. */
@SpringBootTest
@AutoConfigureMockMvc
class LeaderboardContractTest {

    @Autowired
    MockMvc mvc;

    @Test
    void theTopThreeShareRanksAndCountTheTieThatDidNotFit() throws Exception {
        mvc.perform(get("/quizzes/3/leaderboard").param("top", "3")).andExpect(status().isOk())
                .andExpect(content().json("""
                        {"quizId":3,"title":"Algebra sprint","participants":12,"moreTiedAtCutoff":1,"rows":[
                          {"rank":1,"denseRank":1,"studentId":"S-1001","name":"Aarav","score":95,"seconds":300},
                          {"rank":2,"denseRank":2,"studentId":"S-1002","name":"Diya","score":92,"seconds":280},
                          {"rank":3,"denseRank":3,"studentId":"S-1003","name":"Kabir","score":88,"seconds":250}]}""", JsonCompareMode.STRICT));
    }

    @Test
    void theDefaultIsTheTopTen() throws Exception {
        mvc.perform(get("/quizzes/3/leaderboard"))
                .andExpect(jsonPath("$.rows.length()").value(10))
                .andExpect(jsonPath("$.rows[*].rank", contains(1, 2, 3, 3, 5, 6, 6, 8, 9, 10)))
                .andExpect(jsonPath("$.moreTiedAtCutoff").value(1));
    }

    @Test
    void myPlaceIsMyRankAmongEveryone() throws Exception {
        mvc.perform(get("/quizzes/3/leaderboard/me").header("X-Student-Id", "s-1011")).andExpect(status().isOk())
                .andExpect(content().json("""
                        {"quizId":3,"studentId":"S-1011","name":"Reyansh","score":70,"seconds":270,"rank":10,"denseRank":8,"participants":12}""", JsonCompareMode.STRICT));
    }

    @Test
    void unknownQuizzesAndStudentsAre404() throws Exception {
        mvc.perform(get("/quizzes/99/leaderboard")).andExpect(status().isNotFound())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.title").value("Quiz not found"));
        mvc.perform(get("/quizzes/3/leaderboard/me").header("X-Student-Id", "S-9999")).andExpect(status().isNotFound())
                .andExpect(jsonPath("$.title").value("No attempt"));
    }

    @Test
    void badParametersAre400() throws Exception {
        mvc.perform(get("/quizzes/3/leaderboard").param("top", "0")).andExpect(status().isBadRequest());
        mvc.perform(get("/quizzes/3/leaderboard").param("top", "101")).andExpect(status().isBadRequest());
        mvc.perform(get("/quizzes/3/leaderboard").param("top", "ten")).andExpect(status().isBadRequest());
        mvc.perform(get("/quizzes/abc/leaderboard")).andExpect(status().isBadRequest());
        mvc.perform(get("/quizzes/3/leaderboard/me")).andExpect(status().isBadRequest());
        mvc.perform(get("/quizzes/3/leaderboard/me").header("X-Student-Id", "Reyansh")).andExpect(status().isBadRequest());
    }
}
