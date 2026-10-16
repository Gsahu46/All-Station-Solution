package com.kartwala.catalog;

import org.bson.Document;
import org.bson.types.ObjectId;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.data.domain.Sort;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.aggregation.Aggregation;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.Map;
import java.util.TreeMap;

@Service
class Catalog {

    private final MongoTemplate mongo;

    Catalog(MongoTemplate mongo) {
        this.mongo = mongo;
    }

    CatalogProduct create(CatalogProduct product) {
        try {
            return mongo.insert(product);
        } catch (DuplicateKeyException e) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "SKU " + product.sku() + " already exists");
        }
    }

    /** Challenge 1. */
    CatalogProduct byId(String id) {
        if (!ObjectId.isValid(id)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Not a product id: " + id);
        }
        CatalogProduct product = mongo.findById(new ObjectId(id), CatalogProduct.class);
        if (product == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "No product " + id);
        }
        return product;
    }

    /** Challenge 2: $match the category and products having the attribute, then $group by its value. */
    Map<String, Integer> facet(String category, String facet) {
        Map<String, Integer> counts = new TreeMap<>();
        mongo.aggregate(Aggregation.newAggregation(
                        Aggregation.match(Criteria.where("category").is(category).and("attributes." + facet).exists(true)),
                        Aggregation.group("attributes." + facet).count().as("n")), "products", Document.class)
                .getMappedResults().forEach(d -> counts.put(d.getString("_id"), d.getInteger("n")));
        return counts;
    }

    /**
     * Every filter is an equality on attributes.&lt;name&gt;. Names were checked against a pattern first, so no one can
     * pass "$where" or a dotted path; values are plain strings, never parsed as query operators.
     */
    List<CatalogProduct> search(String category, Map<String, String> attributes) {
        Criteria criteria = new Criteria();
        if (category != null) {
            criteria = criteria.and("category").is(category);
        }
        for (Map.Entry<String, String> a : attributes.entrySet()) {
            criteria = criteria.and("attributes." + a.getKey()).is(a.getValue());
        }
        return mongo.find(new Query(criteria).with(Sort.by("sku")).limit(50), CatalogProduct.class);
    }
}
