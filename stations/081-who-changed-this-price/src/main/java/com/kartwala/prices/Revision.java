package com.kartwala.prices;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import org.hibernate.envers.RevisionEntity;
import org.hibernate.envers.RevisionNumber;
import org.hibernate.envers.RevisionTimestamp;

/** One change set: when (milliseconds since 1970, UTC) and who. Envers creates one per transaction that changes audited rows. */
@Entity
@Table(name = "revisions")
@RevisionEntity(ChangedByListener.class)
class Revision {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @RevisionNumber
    private Long id;

    @RevisionTimestamp
    @Column(name = "changed_at_ms")
    private long changedAtMs;

    @Column(name = "changed_by")
    private String changedBy;

    Long id() {
        return id;
    }

    long changedAtMs() {
        return changedAtMs;
    }

    String changedBy() {
        return changedBy;
    }

    void changedBy(String user) {
        this.changedBy = user;
    }
}
