package com.kartwala.catalog;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.util.Map;

/** One document per product: the fields every product has, and its category's own attributes in one sub-document. */
@Document("products")
record CatalogProduct(@Id String id, String sku, String name, String category, long sellerId, int pricePaise, Map<String, String> attributes) {
}
