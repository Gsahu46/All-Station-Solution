package com.kartwala.attributes;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;

import java.sql.Array;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/** The attribute rules of a category, read from attribute_definitions, and the check a new product must pass. */
@Component
class AttributeRules {

    record Rule(String name, boolean required, List<String> allowed) {
    }

    private final JdbcClient jdbc;

    AttributeRules(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    /** Name to rule, for one category; empty if the category does not exist. */
    Map<String, Rule> of(String category) {
        Map<String, Rule> rules = new LinkedHashMap<>();
        jdbc.sql("SELECT name, required, allowed FROM attribute_definitions WHERE category_code = ? ORDER BY name").param(category)
                .query((rs, i) -> {
                    Array allowed = rs.getArray("allowed");
                    return new Rule(rs.getString("name"), rs.getBoolean("required"), allowed == null ? null : Arrays.asList((String[]) allowed.getArray()));
                }).list().forEach(r -> rules.put(r.name(), r));
        return rules;
    }

    /** Every problem with these attributes, by attribute name; empty means valid. */
    Map<String, String> problems(Map<String, Rule> rules, Map<String, String> attributes) {
        Map<String, String> problems = new TreeMap<>();
        attributes.forEach((name, value) -> {
            Rule rule = rules.get(name);
            if (rule == null) {
                problems.put(name, "not an attribute of this category; known: " + rules.keySet());
            } else if (rule.allowed() != null && !rule.allowed().contains(value)) {
                problems.put(name, "must be one of " + rule.allowed());
            }
        });
        List<String> missing = new ArrayList<>();
        rules.values().stream().filter(r -> r.required() && !attributes.containsKey(r.name())).forEach(r -> missing.add(r.name()));
        missing.forEach(name -> problems.put(name, "is required"));
        return problems;
    }
}
