package com.taskloom.sharing;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class SharingContractTest extends ApiTest {

    @Test
    void accessComesFromTheStrongestRelation() throws Exception {
        open("ravi", "d-roadmap").andExpect(status().isOk()).andExpect(jsonPath("$.yourAccess").value("owner"));
        open("meera", "d-roadmap").andExpect(jsonPath("$.yourAccess").value("editor"));
        open("asha", "d-guidelines").andExpect(jsonPath("$.yourAccess").value("viewer")).andExpect(jsonPath("$.title").value("Brand guidelines"));
    }

    @Test
    void accessFlowsThroughFoldersAndTeamsInTeams() throws Exception {
        open("asha", "d-logo-brief").andExpect(status().isOk());    // Logos is inside Brand
        open("neha", "d-guidelines").andExpect(status().isOk());    // brand-leads is inside design
    }

    @Test
    void anEditorSharesWithAUserAndTheyCanOpenIt() throws Exception {
        open("kabir", "d-roadmap").andExpect(status().isNotFound());
        share("meera", "d-roadmap", "user:kabir", "viewer").andExpect(status().isCreated()).andExpect(jsonPath("$.subject").value("user:kabir"));
        open("kabir", "d-roadmap").andExpect(status().isOk()).andExpect(jsonPath("$.yourAccess").value("viewer"));
        org.assertj.core.api.Assertions.assertThat(jdbc.sql("SELECT shared_by FROM share_notices").query(String.class).single()).isEqualTo("meera");
    }

    @Test
    void sharingWithATeamReachesEveryMember() throws Exception {
        share("ravi", "d-roadmap", "team:design", "viewer").andExpect(status().isCreated());
        open("asha", "d-roadmap").andExpect(status().isOk());
        open("neha", "d-roadmap").andExpect(status().isOk());
    }

    @Test
    void sharedWithMeListsWhatICanOpenButDoNotOwn() throws Exception {
        sharedWithMe("asha").andExpect(status().isOk()).andExpect(jsonPath("$[*].title", contains("Brand guidelines", "Logo refresh brief")));
        sharedWithMe("meera").andExpect(jsonPath("$[*].id", contains("d-roadmap"))).andExpect(jsonPath("$[0].access").value("editor"));
        sharedWithMe("ravi").andExpect(jsonPath("$").isEmpty());
    }

    @Test
    void unknownDocumentsAre404AndBadSharesAre400() throws Exception {
        open("ravi", "d-nothing").andExpect(status().isNotFound()).andExpect(jsonPath("$.detail").value("No such document"));
        share("ravi", "d-roadmap", "user:nobody", "viewer").andExpect(status().isBadRequest()).andExpect(jsonPath("$.detail").value("No such user or team"));
        share("ravi", "d-roadmap", "team:nobody", "viewer").andExpect(status().isBadRequest());
        share("ravi", "d-roadmap", "user:kabir", "owner").andExpect(status().isBadRequest());
        share("ravi", "d-roadmap", "group:all", "viewer").andExpect(status().isBadRequest());
    }
}
