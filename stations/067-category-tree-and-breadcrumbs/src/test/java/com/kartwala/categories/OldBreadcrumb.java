package com.kartwala.categories;

import org.springframework.jdbc.core.simple.JdbcClient;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

/** The breadcrumb as it was, kept in the tests only: one query per level, walking up until there is no parent. */
class OldBreadcrumb {

    private final JdbcClient jdbc;
    private final String table;
    int queries;

    OldBreadcrumb(JdbcClient jdbc, String table) {
        this.jdbc = jdbc;
        this.table = table;
    }

    /** {@code stopAfter} is the test's own safety net; the old code had none. */
    List<String> breadcrumb(long id, int stopAfter) {
        List<String> names = new ArrayList<>();
        Long current = id;
        while (current != null && queries < stopAfter) {
            queries++;
            Map<String, Object> row = jdbc.sql("SELECT name, parent_id FROM " + table + " WHERE id = ?").param(current).query().singleRow();
            names.add((String) row.get("name"));
            current = (Long) row.get("parent_id");
        }
        Collections.reverse(names);
        return names;
    }
}
