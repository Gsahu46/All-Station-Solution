package com.kartwala.catalog;

import com.mongodb.MongoWriteException;
import org.bson.Document;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.mongodb.core.aggregation.Aggregation;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.transaction.support.TransactionTemplate;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The collection's rules as MongoDB enforces them, with the driver directly (no Java validation), plus a transaction and an aggregation. */
class CatalogDatabaseTest extends ApiTest {

    @Autowired
    TransactionTemplate transaction;

    private static Document doc(String sku, Object paise, Object attributes) {
        return new Document("sku", sku).append("name", "Test").append("category", "phones").append("sellerId", 7L)
                .append("pricePaise", paise).append("attributes", attributes);
    }

    private void insert(Document d) {
        mongo.getCollection("products").insertOne(d);
    }

    @Test
    void theValidatorAndTheUniqueIndexHoldWithoutJava() {
        assertThatThrownBy(() -> insert(doc("T-NEG", -5, new Document()))).isInstanceOf(MongoWriteException.class).hasMessageContaining("Document failed validation");
        assertThatThrownBy(() -> insert(doc("T-NUM", 99900, new Document("ram", 8)))).hasMessageContaining("Document failed validation");   // a number where text belongs
        assertThatThrownBy(() -> insert(doc("t-lower", 99900, new Document()))).hasMessageContaining("Document failed validation");
        assertThatThrownBy(() -> insert(new Document("sku", "T-BARE"))).hasMessageContaining("Document failed validation");
        assertThatThrownBy(() -> insert(doc("PH-NOVA-8-128", 99900, new Document()))).hasMessageContaining("E11000").hasMessageContaining("products_sku_unique");
    }

    @Test
    void aTransactionMakesSeveralDocumentsAllOrNothing() {
        assertThatThrownBy(() -> transaction.executeWithoutResult(tx -> {
            mongo.insert(doc("T-ONE", 99900, new Document()), "products");
            mongo.insert(doc("T-TWO", 99900, new Document()), "products");
            mongo.insert(doc("T-THREE", 0, new Document()), "products");   // the validator refuses this one
        })).hasMessageContaining("Document failed validation");
        assertThat(mongo.count(new Query(Criteria.where("sku").regex("^T-")), "products")).isZero();
    }

    @Test
    void attributeSearchesUseTheWildcardIndex() {
        Document plan = mongo.getCollection("products").find(new Document("attributes.ram", "8GB")).explain();
        String winning = plan.get("queryPlanner", Document.class).get("winningPlan", Document.class).toJson();
        assertThat(winning).contains("IXSCAN").contains("products_attributes_wildcard");
    }

    @Test
    void anAggregationCountsProductsPerCategory() {
        List<Document> counts = mongo.aggregate(Aggregation.newAggregation(
                Aggregation.group("category").count().as("products"), Aggregation.sort(org.springframework.data.domain.Sort.by("_id"))), "products", Document.class).getMappedResults();
        assertThat(counts).extracting(d -> d.getString("_id") + "=" + d.getInteger("products")).containsExactly("phones=3", "shoes=3");
    }
}
