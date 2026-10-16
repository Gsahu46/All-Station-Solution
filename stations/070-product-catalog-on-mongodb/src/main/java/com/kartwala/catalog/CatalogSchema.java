package com.kartwala.catalog;

import com.mongodb.client.MongoDatabase;
import com.mongodb.client.model.CreateCollectionOptions;
import com.mongodb.client.model.IndexOptions;
import com.mongodb.client.model.ValidationOptions;
import org.bson.Document;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * MongoDB has no migrations here, so the app makes sure, at start, that the collection has its rules: a $jsonSchema
 * validator the server applies to every write, and the indexes. Safe to run on every start.
 */
@Component
@Order(1)
class CatalogSchema implements ApplicationRunner {

    static final String VALIDATOR = """
            {"$jsonSchema": {
              "bsonType": "object",
              "required": ["sku", "name", "category", "sellerId", "pricePaise", "attributes"],
              "properties": {
                "sku": {"bsonType": "string", "pattern": "^[A-Z0-9-]{3,30}$"},
                "name": {"bsonType": "string", "minLength": 1, "maxLength": 120},
                "category": {"bsonType": "string", "pattern": "^[a-z]{2,30}$"},
                "sellerId": {"bsonType": "long"},
                "pricePaise": {"bsonType": "int", "minimum": 100, "maximum": 10000000},
                "attributes": {"bsonType": "object", "maxProperties": 20, "additionalProperties": {"bsonType": "string", "maxLength": 40}}
              }}}""";

    private final MongoTemplate mongo;

    CatalogSchema(MongoTemplate mongo) {
        this.mongo = mongo;
    }

    @Override
    public void run(ApplicationArguments args) {
        MongoDatabase db = mongo.getDb();
        if (!mongo.collectionExists("products")) {
            db.createCollection("products", new CreateCollectionOptions().validationOptions(new ValidationOptions().validator(Document.parse(VALIDATOR))));
        }
        var products = db.getCollection("products");
        products.createIndex(new Document("sku", 1), new IndexOptions().name("products_sku_unique").unique(true));
        products.createIndex(new Document("category", 1).append("sku", 1), new IndexOptions().name("products_category_sku"));
        // A wildcard index: one index over every key inside attributes, whatever keys a category brings.
        products.createIndex(new Document("attributes.$**", 1), new IndexOptions().name("products_attributes_wildcard"));
        if (products.countDocuments() == 0) {
            products.insertMany(List.of(
                    product("PH-NOVA-8-128", "Nova 5G", "phones", 7, 1899900, new Document("ram", "8GB").append("storage", "128GB").append("colour", "Blue")),
                    product("PH-NOVA-8-256", "Nova 5G", "phones", 7, 2199900, new Document("ram", "8GB").append("storage", "256GB").append("colour", "Blue")),
                    product("PH-ZEN-6-128", "Zen Lite", "phones", 7, 1299900, new Document("ram", "6GB").append("storage", "128GB")),
                    product("SH-RUN-9-BLK", "Road Runner", "shoes", 8, 349900, new Document("size", "9").append("colour", "Black").append("material", "mesh")),
                    product("SH-OXF-9-BRN", "Oxford Classic", "shoes", 8, 599900, new Document("size", "9").append("colour", "Brown").append("material", "leather")),
                    product("SH-OXF-10-BRN", "Oxford Classic", "shoes", 8, 599900, new Document("size", "10").append("colour", "Brown").append("material", "leather"))));
        }
    }

    private static Document product(String sku, String name, String category, long seller, int paise, Document attributes) {
        return new Document("sku", sku).append("name", name).append("category", category).append("sellerId", seller)
                .append("pricePaise", paise).append("attributes", attributes);
    }
}
