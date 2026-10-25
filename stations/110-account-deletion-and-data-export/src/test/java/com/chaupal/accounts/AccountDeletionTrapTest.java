package com.chaupal.accounts;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Imran asks Chaupal to delete his account. Where is his phone number afterwards? Written first. */
class AccountDeletionTrapTest extends ApiTest {

    /** The old way: delete what hangs off his user id, blank his row. Every table found through the user id is clean. */
    void oldDelete(long user) {
        for (String table : new String[]{"profiles", "comments", "posts", "login_events", "support_tickets", "data_exports"}) {
            jdbc.sql("DELETE FROM " + table + " WHERE user_id = ?").param(user).update();
        }
        jdbc.sql("UPDATE users SET login = NULL, password_hash = NULL, name = NULL, phone = NULL, email = NULL, status = 'DELETED', deleted_at = now() WHERE id = ?")
                .param(user).update();
    }

    @Test
    void theOldWayLeavesHisNumberInTablesThatDoNotKnowHisUserId() {
        assertThat(foundIn(IMRANS_DIGITS)).hasSizeGreaterThan(5);   // before: everywhere
        oldDelete(1);
        assertThat(foundIn(IMRANS_DIGITS)).containsExactlyInAnyOrder(
                "contact_uploads.contact_phone",   // in Zoya's address book upload
                "invoices.buyer_phone",            // kept by law: fine
                "notification_outbox.phone",       // a message still waiting to be sent to him
                "otp_requests.phone");             // his sign-in codes
    }

    @Test
    void theApiErasesHimEverywhereExceptWhatTheLawKeeps() throws Exception {
        deleteMe("imran").andExpect(status().isAccepted());
        eraseNow(1);
        assertThat(foundIn(IMRANS_DIGITS)).containsExactly("invoices.buyer_phone");
        assertThat(foundIn("Imran Qureshi")).containsExactly("invoices.buyer_name");
        assertThat(foundIn("imran.q@example.com")).isEmpty();
        assertThat(foundIn("Gomti Nagar")).as("his post").isEmpty();
        assertThat(foundIn("Book club")).as("Zoya's post is hers").isNotEmpty();
        as("imran", get("/me/data-exports/1")).andExpect(status().isUnauthorized());   // the account is closed
    }
}
