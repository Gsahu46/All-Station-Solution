package com.kartwala.prices;

import jakarta.persistence.EntityManager;
import org.hibernate.envers.AuditReaderFactory;
import org.hibernate.envers.RevisionType;
import org.hibernate.envers.query.AuditEntity;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

@Service
class Prices {

    record Entry(long revision, Instant changedAt, String changedBy, String change, long pricePaise, Long previousPricePaise) {
    }

    private final Products products;
    private final EntityManager em;

    Prices(Products products, EntityManager em) {
        this.products = products;
        this.em = em;
    }

    /** A seller reaches their own listings; an admin all of them; support reads any history. Anyone else's listing is a 404. */
    private Product reachable(Authentication who, long id, boolean toChange) {
        Product p = products.findById(id).orElseThrow(Prices::notFound);
        boolean all = has(who, "ROLE_ADMIN") || (!toChange && has(who, "ROLE_SUPPORT"));
        if (!all && !p.seller().equals(who.getName())) {
            throw notFound();
        }
        return p;
    }

    private static boolean has(Authentication who, String role) {
        return who.getAuthorities().stream().anyMatch(a -> a.getAuthority().equals(role));
    }

    /** Hibernate writes the new price; Envers, in the same transaction, the revision (who, when) and the row as it now is. */
    @Transactional
    Product changePrice(Authentication who, long id, long pricePaise) {
        Product p = reachable(who, id, true);
        p.changePrice(pricePaise);
        return p;
    }

    /** Newest first, each with the price before it; only changes from (inclusive) to (exclusive). */
    @Transactional(readOnly = true)
    List<Entry> history(Authentication who, long id, Instant from, Instant to) {
        reachable(who, id, false);
        @SuppressWarnings("unchecked")
        List<Object[]> rows = AuditReaderFactory.get(em).createQuery().forRevisionsOfEntity(Product.class, false, true)
                .add(AuditEntity.id().eq(id)).addOrder(AuditEntity.revisionNumber().asc()).getResultList();
        List<Entry> entries = new ArrayList<>();
        Long previous = null;
        for (Object[] row : rows) {
            Product p = (Product) row[0];
            Revision r = (Revision) row[1];
            entries.add(new Entry(r.id(), Instant.ofEpochMilli(r.changedAtMs()), r.changedBy(), ((RevisionType) row[2]).name(), p.pricePaise(), previous));
            previous = p.pricePaise();
        }
        return entries.reversed().stream().filter(e -> !e.changedAt().isBefore(from) && e.changedAt().isBefore(to)).toList();
    }

    record PriceAt(long pricePaise, String setBy, Instant since) {
    }

    /** The last revision at or before the moment, read back as the product was then. */
    @Transactional(readOnly = true)
    PriceAt priceAt(Authentication who, long id, Instant time) {
        reachable(who, id, false);
        @SuppressWarnings("unchecked")
        List<Object[]> rows = AuditReaderFactory.get(em).createQuery().forRevisionsOfEntity(Product.class, false, true)
                .add(AuditEntity.id().eq(id)).add(AuditEntity.revisionProperty("changedAtMs").le(time.toEpochMilli()))
                .addOrder(AuditEntity.revisionNumber().desc()).setMaxResults(1).getResultList();
        if (rows.isEmpty()) {
            throw notFound();
        }
        Revision r = (Revision) rows.getFirst()[1];
        return new PriceAt(((Product) rows.getFirst()[0]).pricePaise(), r.changedBy(), Instant.ofEpochMilli(r.changedAtMs()));
    }

    static ResponseStatusException notFound() {
        return new ResponseStatusException(HttpStatus.NOT_FOUND, "No such product");
    }
}
