package com.billora.invoices;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/** Shared setup: the whole app through MockMvc, and the office invoice used across the tests. */
@SpringBootTest
@AutoConfigureMockMvc
abstract class ApiTest {

    /** 3 T-shirts at Rs 799 (5%) and three 18% lines whose 9% halves each end in half a paisa. Rs 4,794.50 taxable. */
    static final String OFFICE_LINES = """
            [{"description":"Team T-shirt","hsn":"6109","quantity":3,"unitPricePaise":79900},
             {"description":"Keyboard","hsn":"8471","quantity":1,"unitPricePaise":124950},
             {"description":"Mouse","hsn":"8471","quantity":1,"unitPricePaise":54950},
             {"description":"USB cable","hsn":"8544","quantity":3,"unitPricePaise":19950}]""";

    @Autowired
    MockMvc mvc;

    ResultActions preview(String date, String placeOfSupply, String lines) throws Exception {
        return mvc.perform(post("/invoices/tax-preview").contentType(MediaType.APPLICATION_JSON).content(
                "{\"invoiceDate\":\"" + date + "\",\"placeOfSupply\":\"" + placeOfSupply + "\",\"lines\":" + lines + "}"));
    }

    static String oneLine(String hsn, long unitPricePaise) {
        return "[{\"description\":\"Item\",\"hsn\":\"" + hsn + "\",\"quantity\":1,\"unitPricePaise\":" + unitPricePaise + "}]";
    }
}
