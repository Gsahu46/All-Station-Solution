package com.taskloom.board;

import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Written first. The old board saved whatever the editor sent: last write wins. Two managers open the same card;
 * one moves it to "doing", the other reassigns it, both press Save. Each test runs the old way, then the API.
 */
class LastWriteWinsTrapTest extends ApiTest {

    /** The old save, as it was: the whole card from the editor's screen replaces the stored one. */
    static final class OldBoard {
        final Map<String, String> card = new HashMap<>(Map.of("status", "open", "assignee", "asha"));

        Map<String, String> open() {
            return new HashMap<>(card);
        }

        void save(Map<String, String> screen) {
            card.putAll(screen);
        }
    }

    @Test
    void theOldBoardSilentlyDroppedOneManagersChange() {
        OldBoard old = new OldBoard();
        Map<String, String> meera = old.open();
        Map<String, String> kabir = old.open();
        meera.put("status", "doing");
        old.save(meera);
        kabir.put("assignee", "ravi");
        old.save(kabir);   // kabir's screen still says "open"
        assertThat(old.card).containsEntry("assignee", "ravi").containsEntry("status", "open");   // meera's change is gone, and nobody was told
    }

    @Test
    void theSecondSaveOnTheSameVersionIsRefusedAndNothingIsLost() throws Exception {
        String bothRead = etag(1);
        edit(1, bothRead, body("Write the press release", "doing", "asha")).andExpect(status().isOk());       // meera
        edit(1, bothRead, body("Write the press release", "open", "ravi")).andExpect(status().isPreconditionFailed())   // kabir, from the old copy
                .andExpect(jsonPath("$.detail").value("Someone changed this task after you read it. Read it again, then edit."));
        read(1).andExpect(jsonPath("$.status").value("doing")).andExpect(jsonPath("$.assignee").value("asha"));
        // kabir reads again, sees meera's change, and makes his on top of it.
        edit(1, etag(1), body("Write the press release", "doing", "ravi")).andExpect(status().isOk()).andExpect(header().string("ETag", "\"2\""));
        read(1).andExpect(jsonPath("$.status").value("doing")).andExpect(jsonPath("$.assignee").value("ravi"));
    }
}
