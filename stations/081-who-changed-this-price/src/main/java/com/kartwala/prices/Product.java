package com.kartwala.prices;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import org.hibernate.envers.Audited;

/** A listing. @Audited: every change Hibernate writes is also written, as a whole row, to products_aud. */
@Entity
@Table(name = "products")
@Audited
class Product {

    @Id
    private Long id;
    private String seller;
    private String name;
    @Column(name = "price_paise")
    private long pricePaise;

    protected Product() {
    }

    Long id() {
        return id;
    }

    String seller() {
        return seller;
    }

    String name() {
        return name;
    }

    long pricePaise() {
        return pricePaise;
    }

    void changePrice(long pricePaise) {
        this.pricePaise = pricePaise;
    }
}
