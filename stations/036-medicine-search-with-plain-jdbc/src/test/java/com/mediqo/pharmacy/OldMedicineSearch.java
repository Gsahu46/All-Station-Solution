package com.mediqo.pharmacy;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;

/** The search before the fix, kept only in tests. Two bugs: SQL built from the user's text, and nothing closed. */
final class OldMedicineSearch {

    private OldMedicineSearch() {
    }

    static List<String> byName(DataSource dataSource, String name) throws SQLException {
        Connection connection = dataSource.getConnection();   // never closed: the pool never gets it back
        Statement statement = connection.createStatement();
        ResultSet rows = statement.executeQuery(
                "SELECT name, strength, form FROM medicines WHERE name ILIKE '%" + name + "%' ORDER BY name");
        List<String> found = new ArrayList<>();
        while (rows.next()) {
            found.add(rows.getString(1) + " | " + rows.getString(2) + " | " + rows.getString(3));
        }
        return found;
    }
}
