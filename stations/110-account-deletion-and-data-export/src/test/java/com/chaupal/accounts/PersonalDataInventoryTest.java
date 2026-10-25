package com.chaupal.accounts;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/** The inventory and the database must list the same tables: a new table needs a decision before it ships. */
class PersonalDataInventoryTest extends ApiTest {

    @Test
    void everyTableHasAnEntryInTheInventoryAndEveryEntryATable() {
        List<String> tables = jdbc.sql("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY 1")
                .query(String.class).list();
        List<String> listed = PersonalData.INVENTORY.stream().map(PersonalData.Entry::table).sorted().toList();
        assertThat(listed).containsExactlyElementsOf(tables);
    }

    @Test
    void everyEntryThatKeepsOrDeletesSaysWhy() {
        assertThat(PersonalData.INVENTORY).allMatch(e -> !e.why().isBlank());
        assertThat(PersonalData.INVENTORY).filteredOn(e -> e.action() == PersonalData.Action.DELETE).allMatch(e -> e.sql() != null);
    }
}
