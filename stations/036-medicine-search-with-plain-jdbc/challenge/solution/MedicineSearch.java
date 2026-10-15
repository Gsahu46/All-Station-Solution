package com.mediqo.pharmacy;

import org.springframework.stereotype.Repository;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * The search in plain JDBC, with an optional form filter and a total. The SQL is assembled only from fixed fragments
 * written here; every value the user sends is a parameter.
 */
@Repository
class MedicineSearch {

    static final int LIMIT = 20;

    record Page(long total, List<Medicine> results) {
    }

    private final DataSource dataSource;

    MedicineSearch(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    List<Medicine> byName(String text) throws SQLException {
        return byName(text, null, LIMIT).results();
    }

    Page byName(String text, String form, int size) throws SQLException {
        String sql = "SELECT id, name, strength, form, price_paise, prescription_required, count(*) OVER () AS total"
                + " FROM medicines WHERE lower(name) LIKE ? ESCAPE '\\'"
                + (form == null ? "" : " AND form = ?")
                + " ORDER BY name, strength, form LIMIT ?";
        try (Connection connection = dataSource.getConnection();
             PreparedStatement statement = connection.prepareStatement(sql)) {
            int i = 1;
            statement.setString(i++, "%" + escapeLike(text.toLowerCase(Locale.ROOT)) + "%");
            if (form != null) {
                statement.setString(i++, form);
            }
            statement.setInt(i, size);
            try (ResultSet rows = statement.executeQuery()) {
                List<Medicine> found = new ArrayList<>();
                long total = 0;
                while (rows.next()) {
                    total = rows.getLong("total");   // the count before LIMIT, the same on every row
                    found.add(new Medicine(rows.getLong("id"), rows.getString("name"), rows.getString("strength"),
                            rows.getString("form"), rows.getLong("price_paise"), rows.getBoolean("prescription_required")));
                }
                return new Page(total, found);
            }
        }
    }

    /** In LIKE, % and _ are wildcards. A user typing "%" means the character, not "everything". */
    static String escapeLike(String text) {
        return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_");
    }
}
