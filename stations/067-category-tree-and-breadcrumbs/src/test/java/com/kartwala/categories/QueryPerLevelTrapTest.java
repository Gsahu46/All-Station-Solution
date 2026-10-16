package com.kartwala.categories;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.catchThrowable;

/** Written first. The old loop, on the real tree and on an old copy of it without the cycle check. */
class QueryPerLevelTrapTest extends ApiTest {

    @Autowired
    CategoryTree tree;

    @AfterEach
    void dropOldCopy() {
        jdbc.sql("DROP TABLE IF EXISTS old_categories").update();
    }

    @Test
    void theOldLoopSendsOneQueryPerLevel() {
        OldBreadcrumb old = new OldBreadcrumb(jdbc, "categories");
        assertThat(old.breadcrumb(4, 1000)).containsExactly("Home", "Electronics", "Phones", "Android");
        assertThat(old.queries).isEqualTo(4);
        old.queries = 0;
        old.breadcrumb(112, 1000);
        assertThat(old.queries).isEqualTo(14);   // the new one: always 1 statement, WITH RECURSIVE
        assertThat(tree.breadcrumb(112).trail()).hasSize(14);
    }

    @Test
    void aLoopInTheOldDataKeptTheOldCodeGoingForever() {
        // The old table had no cycle check; an admin moved Electronics under Phones.
        jdbc.sql("CREATE TABLE old_categories AS SELECT id, parent_id, name, slug FROM categories").update();
        jdbc.sql("UPDATE old_categories SET parent_id = 3 WHERE id = 2").update();
        OldBreadcrumb old = new OldBreadcrumb(jdbc, "old_categories");
        old.breadcrumb(4, 1000);
        assertThat(old.queries).isEqualTo(1000);   // stopped only by the test's own limit

        // The recursive query's CYCLE clause stops at the first repeat: Android, Phones, Electronics, then Phones again.
        assertThat(jdbc.sql(CategoryTree.UP.replace("FROM categories", "FROM old_categories"))
                .param("id", 4).query((rs, i) -> rs.getString("name")).list()).containsExactly("Electronics", "Phones", "Android");
    }

    @Test
    void theRealTableRefusesTheMoveThatMadeTheLoop() {
        assertThat(catchThrowable(() -> jdbc.sql("UPDATE categories SET parent_id = 3 WHERE id = 2").update()))
                .hasMessageContaining("categories_no_cycle: category 2 cannot move under its own descendant 3");
        assertThat(tree.breadcrumb(4).path()).isEqualTo("Home > Electronics > Phones > Android");
    }
}
