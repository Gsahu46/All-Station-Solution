package com.taskloom.signin;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpSession;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: Globex allows only its own Google Workspace accounts. Linking an invitation to the Globex workspace
 * needs the ID token's hd (hosted domain) claim to be globex.example; a personal Google account is refused (403)
 * and the invitation stays. Other workspaces are unchanged.
 */
class WorkspaceDomainChallengeTest extends ApiTest {

    @Test
    void globexLinksOnlyItsOwnWorkspaceAccounts() throws Exception {
        String email = "neha-" + java.util.UUID.randomUUID().toString().substring(0, 8) + "@globex.example";
        accounts.invite(email, "Neha", "Globex");
        MockHttpSession personal = new MockHttpSession();
        signIn(personal, newSub(), email).andExpect(status().isForbidden());
        MockHttpSession wrongDomain = new MockHttpSession();
        signIn(wrongDomain, newSub(), email, c -> c.claim("hd", "evil.example")).andExpect(status().isForbidden());
        MockHttpSession workspace = new MockHttpSession();
        signIn(workspace, newSub(), email, c -> c.claim("hd", "globex.example")).andExpect(status().isFound());
        me(workspace).andExpect(jsonPath("$.workspace").value("Globex"));
    }
}
