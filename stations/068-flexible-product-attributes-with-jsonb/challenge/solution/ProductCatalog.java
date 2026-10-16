package com.kartwala.attributes;

import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.server.ResponseStatusException;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.json.JsonMapper;

import java.util.List;
import java.util.Map;
import java.util.TreeMap;

@Service
class ProductCatalog {

    record NewProduct(String sku, String name, String category, long sellerId, int pricePaise, Map<String, String> attributes) {
    }

    record Product(long id, String sku, String name, String category, long sellerId, int pricePaise, Map<String, String> attributes) {
    }

    private static final TypeReference<TreeMap<String, String>> MAP = new TypeReference<>() {
    };
    private static final String COLUMNS = "id, sku, name, category_code, seller_id, price_paise, attributes::text AS attributes";

    private final JdbcClient jdbc;
    private final AttributeRules rules;
    private final JsonMapper json;

    ProductCatalog(JdbcClient jdbc, AttributeRules rules, JsonMapper json) {
        this.jdbc = jdbc;
        this.rules = rules;
        this.json = json;
    }

    Product create(NewProduct p) {
        Map<String, AttributeRules.Rule> categoryRules = rules.of(p.category());
        if (categoryRules.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_CONTENT, "No category " + p.category());
        }
        Map<String, String> problems = rules.problems(categoryRules, p.attributes());
        if (!problems.isEmpty()) {
            ProblemDetail detail = ProblemDetail.forStatusAndDetail(HttpStatus.UNPROCESSABLE_CONTENT, "These attributes do not fit a " + p.category() + " product");
            detail.setProperty("attributes", problems);
            throw new ErrorResponseException(HttpStatus.UNPROCESSABLE_CONTENT, detail, null);
        }
        try {
            long id = jdbc.sql("""
                            INSERT INTO products (sku, name, category_code, seller_id, price_paise, attributes)
                            VALUES (?, ?, ?, ?, ?, CAST(? AS jsonb)) RETURNING id""")
                    .params(p.sku(), p.name(), p.category(), p.sellerId(), p.pricePaise(), json.writeValueAsString(p.attributes()))
                    .query(Long.class).single();
            return byId(id);
        } catch (DuplicateKeyException e) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "SKU " + p.sku() + " already exists");
        } catch (DataIntegrityViolationException e) {
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_CONTENT, "No seller " + p.sellerId());   // the only other foreign key left
        }
    }

    Product byId(long id) {
        return jdbc.sql("SELECT " + COLUMNS + " FROM products WHERE id = ?").param(id).query((rs, i) -> new Product(rs.getLong("id"),
                rs.getString("sku"), rs.getString("name"), rs.getString("category_code"), rs.getLong("seller_id"), rs.getInt("price_paise"),
                json.readValue(rs.getString("attributes"), MAP))).single();
    }

    /** Challenge 1: the rules, for a form. */
    List<AttributeRules.Rule> rulesOf(String category) {
        List<AttributeRules.Rule> list = List.copyOf(rules.of(category).values());
        if (list.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "No category " + category);
        }
        return list;
    }

    /** Challenge 2: GROUP BY one attribute's value (->>), filtered with the same containment as the search. */
    Map<String, Long> facet(String category, String facet, Map<String, String> wanted) {
        if (!rules.of(category).containsKey(facet)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "No attribute " + facet + " for " + category);
        }
        Map<String, Long> counts = new TreeMap<>();
        jdbc.sql("""
                        SELECT attributes->>:facet AS value, count(*) AS n FROM products
                        WHERE category_code = :category AND attributes @> CAST(:wanted AS jsonb) AND attributes->>:facet IS NOT NULL   -- not "attributes ? :facet": JDBC reads that ? as a placeholder
                        GROUP BY 1""")
                .param("facet", facet).param("category", category).param("wanted", json.writeValueAsString(wanted))
                .query((rs, i) -> counts.put(rs.getString("value"), rs.getLong("n"))).list();
        return counts;
    }

    /** Containment (@>): "the attributes include all of these pairs", which the GIN index answers. */
    List<Product> search(String category, Map<String, String> wanted) {
        if (category != null && rules.of(category).isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "No category " + category);
        }
        List<String> known = (category == null ? jdbc.sql("SELECT DISTINCT name FROM attribute_definitions")
                : jdbc.sql("SELECT name FROM attribute_definitions WHERE category_code = ?").param(category)).query(String.class).list();
        wanted.keySet().stream().filter(name -> !known.contains(name)).findFirst().ifPresent(name -> {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "No attribute " + name + (category == null ? "" : " for " + category));
        });
        JdbcClient.StatementSpec query = jdbc.sql("SELECT " + COLUMNS + " FROM products WHERE attributes @> CAST(:wanted AS jsonb)"
                + (category == null ? "" : " AND category_code = :category") + " ORDER BY id LIMIT 50").param("wanted", json.writeValueAsString(wanted));
        if (category != null) {
            query = query.param("category", category);
        }
        return query.query((rs, i) -> new Product(rs.getLong("id"), rs.getString("sku"), rs.getString("name"), rs.getString("category_code"),
                        rs.getLong("seller_id"), rs.getInt("price_paise"), json.readValue(rs.getString("attributes"), MAP))).list();
    }
}
