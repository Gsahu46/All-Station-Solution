package com.mediqo.doctors;

import org.hibernate.LazyInitializationException;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.support.TransactionTemplate;
import tools.jackson.databind.json.JsonMapper;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * The first test written for this station: what the old controller did, returning the Doctor entity as JSON, with
 * the app's own JSON mapper. Two outcomes, both bad, depending on whether a transaction is still open.
 */
class EntityAsJsonTrapTest extends ApiTest {

    @Autowired
    JsonMapper json;
    @Autowired
    TransactionTemplate transaction;
    @Autowired
    DoctorDirectory directory;

    @Test
    void outsideATransactionTheLazyClinicCannotBeLoaded() {
        Doctor doctor = doctors.findById(1L).orElseThrow();   // the clinic is a placeholder until touched
        assertThatThrownBy(() -> json.writeValueAsString(doctor))
                .hasRootCauseInstanceOf(LazyInitializationException.class)
                .hasMessageContaining("no session");
    }

    @Test
    void insideOneEveryPrivateColumnLeaks() {
        // What open-in-view=true would have done: the session stays open while the JSON is written.
        String body = transaction.execute(status -> json.writeValueAsString(doctors.findById(1L).orElseThrow()));
        assertThat(body).contains("\"personalPhone\":\"90000 10001\"", "\"salaryPaise\":45000000",
                "\"internalNotes\":\"On notice period until December\"", "hibernateLazyInitializer");
    }

    @Test
    void theViewHasOnlyWhatTheDirectoryShows() {
        String body = json.writeValueAsString(directory.one(1L).orElseThrow());
        assertThat(body).doesNotContain("personalPhone", "salary", "internalNotes", "hibernate")
                .contains("\"clinic\":\"Mediqo Koregaon Park\"");
    }
}
