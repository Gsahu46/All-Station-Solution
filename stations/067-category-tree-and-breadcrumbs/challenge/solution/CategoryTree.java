package com.kartwala.categories;

import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.stream.Collectors;

/** Both answers in one query each, however deep the tree: PostgreSQL walks it with WITH RECURSIVE. */
@Service
class CategoryTree {

    record Crumb(long id, String name, String slug) {
    }

    record Breadcrumb(long id, String path, List<Crumb> trail) {
    }

    record Node(long id, Long parentId, String name, String slug, int depth) {
    }

    record Descendants(long id, List<Node> descendants) {
    }

    /** Up from the category to the root. CYCLE stops the walk if a loop ever got in, instead of running forever. */
    static final String UP = """
            WITH RECURSIVE up (id, parent_id, name, slug, hops) AS (
                SELECT id, parent_id, name, slug, 0 FROM categories WHERE id = :id
                UNION ALL
                SELECT c.id, c.parent_id, c.name, c.slug, up.hops + 1 FROM categories c JOIN up ON c.id = up.parent_id
            ) CYCLE id SET looped USING visited
            SELECT id, name, slug FROM up WHERE NOT looped ORDER BY hops DESC""";

    /** Down from the category: depth first, siblings by name, so the list reads like an indented menu. */
    static final String DOWN = """
            WITH RECURSIVE down (id, parent_id, name, slug, depth) AS (
                SELECT id, parent_id, name, slug, 0 FROM categories WHERE id = :id
                UNION ALL
                SELECT c.id, c.parent_id, c.name, c.slug, down.depth + 1 FROM categories c JOIN down ON c.parent_id = down.id
            ) SEARCH DEPTH FIRST BY name, id SET menu_order
              CYCLE id SET looped USING visited
            SELECT id, parent_id, name, slug, depth FROM down WHERE NOT looped ORDER BY menu_order""";

    record Child(long id, String name, String slug, boolean hasChildren) {
    }

    private final JdbcClient jdbc;

    CategoryTree(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    Breadcrumb breadcrumb(long id) {
        List<Crumb> trail = jdbc.sql(UP).param("id", id).query(Crumb.class).list();
        if (trail.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "No category " + id);
        }
        return new Breadcrumb(id, trail.stream().map(Crumb::name).collect(Collectors.joining(" > ")), trail);
    }

    /** Challenge 1: one level, with EXISTS for the arrow. */
    List<Child> children(long id) {
        if (jdbc.sql("SELECT count(*) FROM categories WHERE id = ?").param(id).query(Long.class).single() == 0) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "No category " + id);
        }
        return jdbc.sql("""
                        SELECT c.id, c.name, c.slug, EXISTS (SELECT 1 FROM categories g WHERE g.parent_id = c.id) AS has_children
                        FROM categories c WHERE c.parent_id = ? ORDER BY c.name, c.id""")
                .param(id).query(Child.class).list();
    }

    /** Challenge 2: one UPDATE moves the whole branch; the trigger refuses loops, which becomes a 409. */
    Breadcrumb move(long id, long parentId) {
        if (jdbc.sql("SELECT count(*) FROM categories WHERE id IN (?, ?)").params(id, parentId).query(Long.class).single() < (id == parentId ? 1 : 2)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "No such category");
        }
        try {
            jdbc.sql("UPDATE categories SET parent_id = ? WHERE id = ?").params(parentId, id).update();
        } catch (DataIntegrityViolationException e) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "Category " + id + " cannot move under " + parentId + ": that is inside it");
        }
        return breadcrumb(id);
    }

    Descendants descendants(long id) {
        List<Node> tree = jdbc.sql(DOWN).param("id", id).query(Node.class).list();
        if (tree.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "No category " + id);
        }
        return new Descendants(id, tree.subList(1, tree.size()));   // the first row is the category itself
    }
}
