package com.mediqo.pharmacy;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * The database's own rules, tested with plain JDBC and no Java validation in the way: named constraints refuse bad
 * rows from any writer, and a failed statement inside a transaction leaves nothing behind after rollback.
 */
class MedicineDatabaseTest extends ApiTest {

    static final String INSERT = "INSERT INTO medicines (name, strength, form, price_paise, prescription_required) VALUES (?, ?, ?, ?, false)";

    @AfterEach
    void removeTestRows() throws SQLException {
        try (Connection c = dataSource.getConnection(); PreparedStatement s = c.prepareStatement("DELETE FROM medicines WHERE name LIKE 'Test %'")) {
            s.executeUpdate();
        }
    }

    void insert(Connection c, String name, String strength, String form, long paise) throws SQLException {
        try (PreparedStatement s = c.prepareStatement(INSERT)) {
            s.setString(1, name);
            s.setString(2, strength);
            s.setString(3, form);
            s.setLong(4, paise);
            s.executeUpdate();
        }
    }

    long count(String name) throws SQLException {
        try (Connection c = dataSource.getConnection(); PreparedStatement s = c.prepareStatement("SELECT count(*) FROM medicines WHERE name = ?")) {
            s.setString(1, name);
            try (ResultSet r = s.executeQuery()) {
                r.next();
                return r.getLong(1);
            }
        }
    }

    @Test
    void namedConstraintsRefuseBadRowsFromAnyWriter() throws SQLException {
        try (Connection c = dataSource.getConnection()) {
            assertThatThrownBy(() -> insert(c, "Test free", "1 mg", "TABLET", 0)).hasMessageContaining("medicines_price_positive");
            assertThatThrownBy(() -> insert(c, "Test powder", "1 g", "POWDER", 100)).hasMessageContaining("medicines_form_known");
            assertThatThrownBy(() -> insert(c, "PARACETAMOL", "500 mg", "TABLET", 100)).hasMessageContaining("medicines_unique_product");
        }
    }

    @Test
    void aPrescriptionMustPointAtARealMedicine() throws SQLException {
        try (Connection c = dataSource.getConnection(); PreparedStatement s = c.prepareStatement(
                "INSERT INTO prescriptions (patient_name, patient_phone, medicine_id, doctor, issued_on) VALUES ('Test', '0', 999999, 'Dr X', CURRENT_DATE)")) {
            assertThatThrownBy(s::executeUpdate).hasMessageContaining("prescriptions_medicine_fk");
        }
    }

    @Test
    void aFailedStatementInATransactionLeavesNothingAfterRollback() throws SQLException {
        try (Connection c = dataSource.getConnection()) {
            c.setAutoCommit(false);
            try {
                insert(c, "Test good", "5 mg", "TABLET", 500);
                insert(c, "Test bad", "5 mg", "TABLET", -1);   // refused by medicines_price_positive
                c.commit();
            } catch (SQLException refused) {
                c.rollback();
            } finally {
                c.setAutoCommit(true);   // the pool hands this connection to someone else next
            }
        }
        assertThat(count("Test good")).isZero();
        assertThat(count("Test bad")).isZero();
    }

    @Test
    void withAutoCommitTheFirstRowStaysWhenTheSecondFails() throws SQLException {
        try (Connection c = dataSource.getConnection()) {
            insert(c, "Test kept", "5 mg", "TABLET", 500);
            assertThatThrownBy(() -> insert(c, "Test refused", "5 mg", "TABLET", -1)).isInstanceOf(SQLException.class);
        }
        assertThat(count("Test kept")).isEqualTo(1);   // each statement was its own transaction
    }

    @Test
    void escapingKeepsWildcardsLiteral() {
        assertThat(MedicineSearch.escapeLike("50%_off\\")).isEqualTo("50\\%\\_off\\\\");
    }
}
