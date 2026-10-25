package com.chaupal.accounts;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: an export is a copy of everything about a person; it should not sit there for ever. 7 days, then 410. */
class ExportExpiryChallengeTest extends ApiTest {

    @Test
    void aReadyExportCanBeDownloadedForSevenDaysThenItIsGone() throws Exception {
        requestExport("zoya").andExpect(status().isAccepted());
        accounts.runJobs();
        exportFile("zoya", 1).andExpect(status().isOk());

        jdbc.sql("UPDATE data_exports SET ready_at = now() - interval '8 days' WHERE id = 1").update();
        exportFile("zoya", 1).andExpect(status().isGone());
        accounts.runJobs();
        assertThat(jdbc.sql("SELECT content IS NULL FROM data_exports WHERE id = 1").query(Boolean.class).single()).isTrue();
        assertThat(foundIn("meets Friday")).as("the copy inside the export is gone too").containsExactly("posts.body");
    }
}
