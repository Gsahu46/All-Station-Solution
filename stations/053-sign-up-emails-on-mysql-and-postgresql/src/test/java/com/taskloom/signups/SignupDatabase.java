package com.taskloom.signups;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.support.TransactionTemplate;

import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The schema's rules with Java bypassed, a rollback, and a race, written once and run on both databases. */
abstract class SignupDatabase extends ApiTest {

    @Autowired
    TransactionTemplate transaction;

    void insert(String email) {
        jdbc.sql("INSERT INTO signups (email, name) VALUES (?, 'Direct')").param(email).update();
    }

    @Test
    void namedConstraintsHoldWithoutJava() {
        insert("Asha@x.com");
        assertThatThrownBy(() -> insert("asha@X.com")).hasMessageContaining("signups_email_unique");
        assertThatThrownBy(() -> insert("asha.x.com")).hasMessageContaining("signups_email_shape");
        assertThatThrownBy(() -> insert("asha @x.com")).hasMessageContaining("signups_email_shape");
    }

    @Test
    void anAccentMakesADifferentAddressOnBothDatabases() {
        insert("jose@x.com");
        insert("josé@x.com");   // refused on MySQL's default collation; utf8mb4_bin keeps them apart, like PostgreSQL
        assertThat(rows()).isEqualTo(2);
    }

    @Test
    void aBatchWithADuplicateLeavesNothing() {
        assertThatThrownBy(() -> transaction.executeWithoutResult(s -> {
            insert("rohan@x.com");
            insert("meera@x.com");
            insert("ROHAN@x.com");   // the third row breaks the rule; the first two go with it
        })).hasMessageContaining("signups_email_unique");
        assertThat(rows()).isZero();
    }

    @Test
    void tenSpellingsAtOnceMakeOneSignup() throws Exception {
        String[] spellings = {"asha@x.com", "Asha@x.com", "ASHA@x.com", "asha@X.com", "asha@X.COM",
                "aSha@x.com", "asHa@x.com", "ashA@x.com", "ASHA@X.COM", "Asha@X.Com"};
        AtomicInteger next = new AtomicInteger();
        List<Integer> statuses = together(spellings.length, () -> signUp(spellings[next.getAndIncrement()]).andReturn().getResponse().getStatus());
        assertThat(statuses).filteredOn(s -> s == 201).hasSize(1);
        assertThat(statuses).filteredOn(s -> s == 409).hasSize(9);
        assertThat(rows()).isEqualTo(1);
    }
}
