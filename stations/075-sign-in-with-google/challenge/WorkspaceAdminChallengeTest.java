package com.taskloom.signin;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpSession;

import static org.hamcrest.Matchers.hasItem;
import static org.hamcrest.Matchers.not;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: GET /workspace/members lists the names of the signed-in members of the caller's own workspace,
 * for workspace admins only (demo rule: asha is Acme's admin). Other members get 403; nobody sees another workspace.
 */
class WorkspaceAdminChallengeTest extends ApiTest {

    @Test
    void anAdminSeesTheirOwnWorkspaceOnly() throws Exception {
        String other = "lena-" + java.util.UUID.randomUUID().toString().substring(0, 8) + "@initech.example";
        accounts.invite(other, "Lena", "Initech");
        signIn(new MockHttpSession(), newSub(), other);
        MockHttpSession asha = new MockHttpSession();
        signIn(asha, "100000000000000000001", "asha@acme.example");
        mvc.perform(get("/workspace/members").session(asha)).andExpect(status().isOk())
                .andExpect(jsonPath("$", hasItem("Asha Rao"))).andExpect(jsonPath("$", not(hasItem("Lena"))));
    }

    @Test
    void aMemberWhoIsNotAnAdminIs403() throws Exception {
        String email = invite("Tara");
        MockHttpSession tara = new MockHttpSession();
        signIn(tara, newSub(), email);
        mvc.perform(get("/workspace/members").session(tara)).andExpect(status().isForbidden());
        mvc.perform(get("/workspace/members")).andExpect(status().isUnauthorized());
    }
}
