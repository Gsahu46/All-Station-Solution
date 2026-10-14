package com.citylibrary.loans;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract through the whole app: borrowing, returning, a member's loans, and every refusal. */
class LoanContractTest extends ApiTest {

    @Test
    void aBookIsLentForFourteenDays() throws Exception {
        borrow("m-1", "b-1")
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.memberId").value("m-1"))
                .andExpect(jsonPath("$.bookId").value("b-1"))
                .andExpect(jsonPath("$.borrowedOn").value("2026-10-14"))
                .andExpect(jsonPath("$.dueOn").value("2026-10-28"))
                .andExpect(jsonPath("$.returnedOn").doesNotExist());
        mvc.perform(get("/members/m-1/loans")).andExpect(status().isOk()).andExpect(jsonPath("$", hasSize(1)));
    }

    @Test
    void theKioskLendsByCardAndBarcode() throws Exception {
        kiosk(" cl-0001 ", "lib100002").andExpect(status().isCreated()).andExpect(jsonPath("$.bookId").value("b-2"));
    }

    @Test
    void aLateReturnIsFinedFiveRupeesADayAndBlocksTheNextLoan() throws Exception {
        today("2026-10-20");   // Meera's books were due on 15 October
        mvc.perform(post("/loans/l-6/return")).andExpect(status().isOk())
                .andExpect(jsonPath("$.returnedOn").value("2026-10-20"))
                .andExpect(jsonPath("$.finePaise").value(2_500));
        borrow("m-3", "b-1").andExpect(status().isConflict()).andExpect(jsonPath("$.reason").value("UNPAID_FINE"))
                .andExpect(jsonPath("$.detail").value("Meera Iyer has an unpaid fine of Rs 25.00."));
    }

    @Test
    void anOnTimeReturnHasNoFineAndFreesTheBook() throws Exception {
        mvc.perform(post("/loans/l-6/return")).andExpect(jsonPath("$.finePaise").value(0));
        borrow("m-1", "b-6").andExpect(status().isCreated());
    }

    @Test
    void refusalsAre409WithAReason() throws Exception {
        borrow("m-1", "b-7").andExpect(status().isConflict())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.reason").value("BOOK_ON_LOAN"));
        mvc.perform(post("/loans/l-6/return"));
        mvc.perform(post("/loans/l-6/return")).andExpect(status().isConflict()).andExpect(jsonPath("$.reason").value("ALREADY_RETURNED"));
    }

    @Test
    void unknownMembersBooksAndLoansAre404AndBadBodiesAre400() throws Exception {
        borrow("m-9", "b-1").andExpect(status().isNotFound());
        borrow("m-1", "b-99").andExpect(status().isNotFound());
        kiosk("CL-9999", "LIB100001").andExpect(status().isNotFound());
        mvc.perform(post("/loans/l-404/return")).andExpect(status().isNotFound());
        mvc.perform(get("/members/m-9/loans")).andExpect(status().isNotFound());
        borrow("", "b-1").andExpect(status().isBadRequest());
        mvc.perform(post("/loans").contentType(MediaType.APPLICATION_JSON).content("{}")).andExpect(status().isBadRequest());
    }
}
