package com.kartwala.categories;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.DataAccessException;
import org.springframework.transaction.support.TransactionTemplate;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The tree's rules as PostgreSQL enforces them, with plain SQL; test categories have ids from 900 and are removed afterwards. */
class CategoryDatabaseTest extends ApiTest {

    @Autowired
    TransactionTemplate transaction;
    @Autowired
    CategoryTree tree;

    @AfterEach
    void removeTestCategories() {
        jdbc.sql("UPDATE categories SET parent_id = 3 WHERE id = 5").update();   // undo the move test
        jdbc.sql("DELETE FROM categories WHERE id >= 900 AND parent_id >= 900").update();
        jdbc.sql("DELETE FROM categories WHERE id >= 900").update();
    }

    private void category(long id, Long parent, String name, String slug) {
        jdbc.sql("INSERT INTO categories (id, parent_id, name, slug) VALUES (?, ?, ?, ?)").params(id, parent, name, slug).update();
    }

    @Test
    void namedConstraintsHoldWithoutJava() {
        assertThatThrownBy(() -> category(900, 900L, "Itself", "itself")).isInstanceOf(DataAccessException.class).hasMessageContaining("categories_not_own_parent");
        assertThatThrownBy(() -> category(901, 3L, "Android Again", "android")).hasMessageContaining("categories_slug_per_parent");
        assertThatThrownBy(() -> category(902, 999L, "Orphan", "orphan")).hasMessageContaining("categories_parent_fk");
        assertThatThrownBy(() -> category(903, 3L, "Bad Slug", "Bad Slug")).hasMessageContaining("categories_slug_shape");
        assertThatThrownBy(() -> category(904, null, "Second Home", "home")).hasMessageContaining("categories_slug_per_parent");   // NULLS NOT DISTINCT
    }

    @Test
    void aMoveIsOneUpdateAndEveryBreadcrumbFollowsIt() {
        jdbc.sql("UPDATE categories SET parent_id = 2 WHERE id = 5").update();   // iPhone straight under Electronics
        assertThat(tree.breadcrumb(5).path()).isEqualTo("Home > Electronics > iPhone");
    }

    @Test
    void aBranchWithOneBadNodeIsNotAddedAtAll() {
        assertThatThrownBy(() -> transaction.executeWithoutResult(tx -> {
            category(900, 1L, "Groceries", "groceries");
            category(901, 900L, "Fruit", "fruit");
            category(902, 901L, "Mangoes", "Mangoes!");
        })).hasMessageContaining("categories_slug_shape");
        assertThat(jdbc.sql("SELECT count(*) FROM categories WHERE id >= 900").query(Long.class).single()).isZero();
    }
}
