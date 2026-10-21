package com.taskloom.sharing;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class SharingSecurityTest extends ApiTest {

    @Test
    void noOrWrongCredentialsAre401() throws Exception {
        mvc.perform(get("/docs/d-roadmap")).andExpect(status().isUnauthorized()).andExpect(header().string("WWW-Authenticate", "Basic realm=\"taskloom\""));
        mvc.perform(get("/docs/d-roadmap").with(httpBasic("ravi", "guess"))).andExpect(status().isUnauthorized());
    }

    @Test
    void aViewerCannotShareAndAStrangerCannotEvenSee() throws Exception {
        share("asha", "d-guidelines", "user:kabir", "viewer").andExpect(status().isForbidden()).andExpect(jsonPath("$.detail").value("Viewers cannot share"));
        share("kabir", "d-salaries", "user:kabir", "editor").andExpect(status().isNotFound());   // nobody shares themselves in
        open("kabir", "d-salaries").andExpect(status().isNotFound());
    }

    @Test
    void oneUsersAccessIsNotAnothersAndTeamsDoNotLeakAcross() throws Exception {
        open("meera", "d-guidelines").andExpect(status().isNotFound());   // not in design
        open("asha", "d-roadmap").andExpect(status().isNotFound());       // meera's edit right is meera's
        open("asha", "d-salaries").andExpect(status().isNotFound());
    }

    @Test
    void pathsAndMethodsWithoutARuleAreRefused() throws Exception {
        mvc.perform(get("/docs").with(httpBasic("ravi", "ravi-demo-pass"))).andExpect(status().isForbidden());
        mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete("/docs/d-roadmap").with(httpBasic("ravi", "ravi-demo-pass")))
                .andExpect(status().isForbidden());
    }

    @Test
    void aFolderLoopDoesNotHangTheCheck() throws Exception {
        // A bad move left Brand inside Logos inside Brand. The recursive query stops: UNION drops rows it has seen.
        jdbc.sql("INSERT INTO relation_tuples VALUES ('folder', 'f-brand', 'parent', 'folder', 'f-logos', '')").update();
        open("asha", "d-guidelines").andExpect(status().isOk());
        open("kabir", "d-guidelines").andExpect(status().isNotFound());
        sharedWithMe("asha").andExpect(status().isOk());
    }

    @Test
    void oddIdsAndSubjectsAre400Or404NeverAnError() throws Exception {
        for (String id : new String[]{"d-roadmap' OR '1'='1", "..%2Fd-salaries", "D-ROADMAP", "a".repeat(500)}) {
            assertThat(open("ravi", id).andReturn().getResponse().getStatus()).as(id.length() > 40 ? id.substring(0, 40) : id).isIn(400, 404);
        }
        share("ravi", "d-roadmap", "user:kabir' OR '1'='1", "viewer").andExpect(status().isBadRequest());
        share("ravi", "d-roadmap", "team:design#member", "viewer").andExpect(status().isBadRequest());
    }
}
