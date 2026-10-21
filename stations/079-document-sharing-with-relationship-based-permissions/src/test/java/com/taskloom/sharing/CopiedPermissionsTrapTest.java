package com.taskloom.sharing;

import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Written first. The old sharing code copied permissions: sharing a folder with a team wrote one "may read" row per
 * member onto each document in it, at that moment. Each test runs the old way, then the same change in the tuples.
 */
class CopiedPermissionsTrapTest extends ApiTest {

    /** The old store, as it was: document -> users who may read it, filled in when something was shared. */
    static final class OldAcl {
        final Map<String, Set<String>> readers = new HashMap<>();

        void shareFolderWithTeam(List<String> docsInFolder, List<String> teamMembers) {
            docsInFolder.forEach(d -> readers.computeIfAbsent(d, k -> new HashSet<>()).addAll(teamMembers));
        }

        boolean mayRead(String user, String doc) {
            return readers.getOrDefault(doc, Set.of()).contains(user);
        }
    }

    @Test
    void someoneRemovedFromATeamKeptTheTeamsDocuments() throws Exception {
        OldAcl old = new OldAcl();
        old.shareFolderWithTeam(List.of("d-guidelines", "d-logo-brief"), List.of("asha", "neha"));
        // asha leaves the design team. The team changed; the copied rows did not.
        assertThat(old.mayRead("asha", "d-guidelines")).isTrue();

        open("asha", "d-guidelines").andExpect(status().isOk());
        removeFromTeam("asha", "design");
        open("asha", "d-guidelines").andExpect(status().isNotFound());   // the next request already knows
        open("asha", "d-logo-brief").andExpect(status().isNotFound());
        sharedWithMe("asha").andExpect(jsonPath("$").isEmpty());
    }

    @Test
    void aDocumentAddedLaterWasNotSharedAtAll() throws Exception {
        OldAcl old = new OldAcl();
        old.shareFolderWithTeam(List.of("d-guidelines"), List.of("asha"));
        jdbc.sql("INSERT INTO documents (id, title, body) VALUES ('d-new-icons', 'New icon set', 'Draft.')").update();
        jdbc.sql("INSERT INTO relation_tuples VALUES ('doc', 'd-new-icons', 'parent', 'folder', 'f-brand', ''), ('doc', 'd-new-icons', 'owner', 'user', 'ravi', '')").update();
        assertThat(old.mayRead("asha", "d-new-icons")).isFalse();   // nobody copied rows for it
        open("asha", "d-new-icons").andExpect(status().isOk());      // in the folder, so the team can read it
    }

    @Test
    void aDocumentSharedWithATeamFollowsTheTeamAfterwards() throws Exception {
        share("ravi", "d-roadmap", "team:design", "viewer");
        open("asha", "d-roadmap").andExpect(status().isOk());
        removeFromTeam("asha", "design");
        open("asha", "d-roadmap").andExpect(status().isNotFound());
        jdbc.sql("INSERT INTO relation_tuples VALUES ('team', 'design', 'member', 'user', 'kabir', '')").update();
        open("kabir", "d-roadmap").andExpect(status().isOk());   // joined after the share, sees it anyway
    }

    @Test
    void aNewTeamMemberGetsTheTeamsDocuments() throws Exception {
        jdbc.sql("INSERT INTO relation_tuples VALUES ('team', 'design', 'member', 'user', 'kabir', '')").update();
        open("kabir", "d-guidelines").andExpect(status().isOk());
    }
}
