package com.billora.invoicing;

import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

interface InvoiceRepository extends JpaRepository<Invoice, Long> {

    /** Lines are LAZY: without this graph, reading them is a second query. */
    @EntityGraph(attributePaths = "lines")
    Optional<Invoice> findWithLinesById(long id);
}
