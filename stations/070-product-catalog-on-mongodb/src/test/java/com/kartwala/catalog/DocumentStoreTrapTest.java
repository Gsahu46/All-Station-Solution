package com.kartwala.catalog;

import org.bson.Document;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.data.mongodb.core.aggregation.Aggregation;
import org.springframework.data.mongodb.core.aggregation.LookupOperation;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.data.mongodb.core.query.Update;
import org.springframework.transaction.support.TransactionTemplate;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Written first. The team's plan to move orders and stock into MongoDB too, tried on two small examples: an order
 * that touches two collections, and seller names copied into every listing.
 */
class DocumentStoreTrapTest extends ApiTest {

    @Autowired
    TransactionTemplate transaction;

    @BeforeEach
    void collections() {
        mongo.insert(new Document("_id", "PH-NOVA-8-128").append("onHand", 5), "stock");
        mongo.insert(new Document("_id", "ORD-1").append("sku", "PH-NOVA-8-128").append("quantity", 1), "orders");   // yesterday's order
        mongo.insert(new Document("_id", 8L).append("name", "Meera Footwear"), "sellers");
        for (String sku : List.of("SH-RUN-9-BLK", "SH-OXF-9-BRN", "SH-OXF-10-BRN")) {   // each listing carries a copy of the seller's name
            mongo.insert(new Document("_id", sku).append("seller", new Document("id", 8L).append("name", "Meera Footwear")), "listings");
        }
    }

    @AfterEach
    void dropCollections() {
        for (String c : List.of("stock", "orders", "sellers", "listings")) {
            mongo.dropCollection(c);
        }
    }

    private int onHand() {
        return mongo.findById("PH-NOVA-8-128", Document.class, "stock").getInteger("onHand");
    }

    /** Take one from stock, then record the order: two writes, two collections. */
    private void placeOrder(String orderNo) {
        mongo.updateFirst(new Query(Criteria.where("_id").is("PH-NOVA-8-128").and("onHand").gte(1)), new Update().inc("onHand", -1), "stock");
        mongo.insert(new Document("_id", orderNo).append("sku", "PH-NOVA-8-128").append("quantity", 1), "orders");
    }

    @Test
    void withoutATransactionAFailedOrderStillTakesStock() {
        assertThatThrownBy(() -> placeOrder("ORD-1")).isInstanceOf(DuplicateKeyException.class);   // a retried request reuses the order number
        assertThat(onHand()).isEqualTo(4);   // one phone gone, no order to show for it
    }

    @Test
    void aTransactionPutsTheStockBack() {
        assertThatThrownBy(() -> transaction.executeWithoutResult(tx -> placeOrder("ORD-1"))).isInstanceOf(DuplicateKeyException.class);
        assertThat(onHand()).isEqualTo(5);
    }

    @Test
    void copiedSellerNamesGoStaleAndALookupIsTheJoin() {
        mongo.updateFirst(new Query(Criteria.where("_id").is(8L)), new Update().set("name", "Meera Shoes & Sandals"), "sellers");
        assertThat(mongo.findAll(Document.class, "listings")).extracting(d -> d.get("seller", Document.class).getString("name"))
                .containsOnly("Meera Footwear");   // every copy still has the old name, until someone updates all of them
        // The fresh name needs a $lookup: MongoDB's join, written as an aggregation stage, run for every read.
        LookupOperation lookup = Aggregation.lookup("sellers", "seller.id", "_id", "current");
        List<Document> joined = mongo.aggregate(Aggregation.newAggregation(lookup, Aggregation.unwind("current")), "listings", Document.class).getMappedResults();
        assertThat(joined).extracting(d -> d.get("current", Document.class).getString("name")).containsOnly("Meera Shoes & Sandals");
    }
}
