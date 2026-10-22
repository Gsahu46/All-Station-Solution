package com.mediqo.roster;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.SQLException;
import java.sql.Statement;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.catchThrowable;

/**
 * Written first. The old code ran "count the doctors on call; if more than one, take me off" in a READ COMMITTED
 * transaction, the default. Two doctors at the same moment each counted two, each took themselves off, and the
 * ward had nobody. These tests drive two real database transactions step by step, so the bad order happens every time.
 */
class WriteSkewTrapTest extends ApiTest {

    @Autowired
    DataSource dataSource;

    Connection begin(int isolation) throws SQLException {
        Connection c = dataSource.getConnection();
        c.setAutoCommit(false);
        c.setTransactionIsolation(isolation);
        return c;
    }

    static int countOnCall(Connection c) throws SQLException {
        try (var rs = c.createStatement().executeQuery("SELECT count(*) FROM roster WHERE ward = 'cardiology' AND on_call")) {
            rs.next();
            return rs.getInt(1);
        }
    }

    static void goOff(Connection c, String doctor) throws SQLException {
        try (Statement s = c.createStatement()) {
            s.executeUpdate("UPDATE roster SET on_call = false WHERE ward = 'cardiology' AND doctor = '" + doctor + "'");
        }
    }

    @Test
    void underReadCommittedBothDoctorsLeftAndTheWardHadNobody() throws Exception {
        jdbc.sql("ALTER TABLE roster DISABLE TRIGGER wards_keep_min_on_call").update();   // the old schema had no such rule
        try (Connection sharma = begin(Connection.TRANSACTION_READ_COMMITTED); Connection iyer = begin(Connection.TRANSACTION_READ_COMMITTED)) {
            assertThat(countOnCall(sharma)).isEqualTo(2);   // "iyer is still on call, I can go"
            assertThat(countOnCall(iyer)).isEqualTo(2);     // "sharma is still on call, I can go"
            goOff(sharma, "dr.sharma");
            goOff(iyer, "dr.iyer");                         // different rows: nothing waits, nothing conflicts
            sharma.commit();
            iyer.commit();
        } finally {
            jdbc.sql("ALTER TABLE roster ENABLE TRIGGER wards_keep_min_on_call").update();
        }
        assertThat(onCall("cardiology")).isZero();
    }

    @Test
    void underSerializableOneOfThemIsStopped() throws Exception {
        jdbc.sql("ALTER TABLE roster DISABLE TRIGGER wards_keep_min_on_call").update();   // only isolation is tested here
        Throwable stopped;
        try (Connection sharma = begin(Connection.TRANSACTION_SERIALIZABLE); Connection iyer = begin(Connection.TRANSACTION_SERIALIZABLE)) {
            countOnCall(sharma);
            countOnCall(iyer);
            goOff(sharma, "dr.sharma");
            goOff(iyer, "dr.iyer");
            sharma.commit();
            stopped = catchThrowable(iyer::commit);
            iyer.rollback();
        } finally {
            jdbc.sql("ALTER TABLE roster ENABLE TRIGGER wards_keep_min_on_call").update();
        }
        assertThat(stopped).isInstanceOf(SQLException.class);
        assertThat(((SQLException) stopped).getSQLState()).isEqualTo("40001");   // could not serialize: run it again
        assertThat(onCall("cardiology")).isEqualTo(1);
    }
}
