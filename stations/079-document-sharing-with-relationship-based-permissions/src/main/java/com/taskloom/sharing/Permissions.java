package com.taskloom.sharing;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Optional;

/**
 * Relationship-based access, worked out from the tuples on every call (Zanzibar-style, in plain PostgreSQL).
 * A user is: themselves, and every team they are in, through teams in teams. A document is: itself, and every folder
 * above it. Access is the strongest relation any of the first has to any of the second.
 */
@Component
class Permissions {

    static final List<String> LEVELS = List.of("viewer", "editor", "owner");

    /** The user and every team they belong to, directly or through other teams. UNION stops at cycles. */
    static final String ME = """
            me(type, id) AS (
                SELECT 'user'::text, ?::text
                UNION
                SELECT t.object_type, t.object_id FROM relation_tuples t JOIN me m ON t.subject_type = m.type AND t.subject_id = m.id
                WHERE t.object_type = 'team' AND t.relation = 'member')""";

    static final String RANK = "CASE t.relation WHEN 'owner' THEN 3 WHEN 'editor' THEN 2 WHEN 'viewer' THEN 1 END";

    private final JdbcClient jdbc;

    Permissions(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    /** viewer, editor or owner; empty if the user has no access at all. */
    Optional<String> access(String user, String docId) {
        int level = jdbc.sql("WITH RECURSIVE " + ME + """
                        ,
                        above(type, id) AS (
                            SELECT 'doc'::text, ?::text
                            UNION
                            SELECT t.subject_type, t.subject_id FROM relation_tuples t JOIN above a ON t.object_type = a.type AND t.object_id = a.id
                            WHERE t.relation = 'parent')
                        SELECT coalesce(max(""" + RANK + """
                        ), 0) FROM relation_tuples t
                        JOIN above a ON t.object_type = a.type AND t.object_id = a.id
                        JOIN me m ON t.subject_type = m.type AND t.subject_id = m.id
                        WHERE t.relation IN ('viewer', 'editor', 'owner')""")
                .params(user, docId).query(Integer.class).single();
        return level == 0 ? Optional.empty() : Optional.of(LEVELS.get(level - 1));   // 0: no tuple matched (single() refuses a null max)
    }

    record Shared(String id, String title, String access) {
    }

    /** Every document the user can open but does not own, with their strongest access. */
    List<Shared> sharedWith(String user) {
        return jdbc.sql("WITH RECURSIVE " + ME + """
                        ,
                        granted(type, id, level) AS (
                            SELECT t.object_type, t.object_id, """ + RANK + """
                            FROM relation_tuples t JOIN me m ON t.subject_type = m.type AND t.subject_id = m.id
                            WHERE t.relation IN ('viewer', 'editor', 'owner')
                            UNION
                            SELECT c.object_type, c.object_id, g.level FROM relation_tuples c JOIN granted g
                                ON c.relation = 'parent' AND c.subject_type = g.type AND c.subject_id = g.id)
                        SELECT d.id, d.title, max(g.level) AS level FROM granted g JOIN documents d ON g.type = 'doc' AND d.id = g.id
                        GROUP BY d.id, d.title HAVING max(g.level) < 3 ORDER BY d.title""")
                .param(user).query((rs, n) -> new Shared(rs.getString("id"), rs.getString("title"), LEVELS.get(rs.getInt("level") - 1))).list();
    }
}
