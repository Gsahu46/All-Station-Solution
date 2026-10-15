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
 * The search in plain JDBC, every step visible. The SQL text is fixed; the user's words travel separately as a
 * parameter, so the database never reads them as SQL. try-with-resources closes the result set, the statement and
 * the connection (which returns it to the pool) on every path, including exceptions.
 */
@Repository
class MedicineSearch {

    static final int LIMIT = 20;

    private static final String SQL = """
            SELECT id, name, strength, form, price_paise, prescription_required
              FROM medicines
             WHERE lower(name) LIKE ? ESCAPE '\\'
             ORDER BY name, strength, form
             LIMIT ?""";

    private final DataSource dataSource;

    MedicineSearch(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    List<Medicine> byName(String text) throws SQLException {
        try (Connection connection = dataSource.getConnection();
             PreparedStatement statement = connection.prepareStatement(SQL)) {
            statement.setString(1, "%" + escapeLike(text.toLowerCase(Locale.ROOT)) + "%");
            statement.setInt(2, LIMIT);
            try (ResultSet rows = statement.executeQuery()) {
                List<Medicine> found = new ArrayList<>();
                while (rows.next()) {
                    found.add(new Medicine(rows.getLong("id"), rows.getString("name"), rows.getString("strength"),
                            rows.getString("form"), rows.getLong("price_paise"), rows.getBoolean("prescription_required")));
                }
                return found;
            }
        }
    }

    /** In LIKE, % and _ are wildcards. A user typing "%" means the character, not "everything". */
    static String escapeLike(String text) {
        return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_");
    }
}
