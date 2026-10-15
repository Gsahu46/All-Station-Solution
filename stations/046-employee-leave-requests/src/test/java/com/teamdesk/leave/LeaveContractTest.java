package com.teamdesk.leave;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The HTTP contract: requests, approvals and balances, valid, invalid and not found. */
class LeaveContractTest extends ApiTest {

    @Test
    void aRequestCountsWorkingDaysAndWaits() throws Exception {
        ask(1, "2026-11-06", "2026-11-10").andExpect(status().isCreated())   // Fri to Tue: Sat and Sun are free
                .andExpect(content().json("""
                        {"id":1,"employeeId":1,"startDate":"2026-11-06","endDate":"2026-11-10","days":3,"status":"PENDING"}"""));
        mvc.perform(get("/employees/1/leave-balance")).andExpect(jsonPath("$.balanceDays").value(12));   // nothing taken yet
    }

    @Test
    void approvalTakesTheDaysAndTheBalanceShowsIt() throws Exception {
        long id = newRequest(1, "2026-11-06", "2026-11-10");
        approve(id).andExpect(status().isOk())
                .andExpect(content().json("""
                        {"requestId":1,"status":"APPROVED","days":3,"employeeId":1,"balanceDays":9}"""));
        mvc.perform(get("/employees/1/leave-balance")).andExpect(status().isOk())
                .andExpect(content().json("""
                        {"employeeId":1,"name":"Asha Verma","balanceDays":9}"""));
    }

    @Test
    void aDecidedRequestCannotBeApprovedAgain() throws Exception {
        long id = newRequest(1, "2026-11-06", "2026-11-10");
        approve(id).andExpect(status().isOk());
        approve(id).andExpect(status().isConflict()).andExpect(jsonPath("$.title").value("Already decided"));
        mvc.perform(get("/employees/1/leave-balance")).andExpect(jsonPath("$.balanceDays").value(9));
    }

    @Test
    void moreDaysThanTheBalanceIs422AndChangesNothing() throws Exception {
        long id = newRequest(2, "2026-11-06", "2026-11-10");   // Rohan has 2 days, asks for 3
        approve(id).andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.detail").value("Rohan Iyer has 2 days left; this request needs 3."));
        mvc.perform(get("/employees/2/leave-balance")).andExpect(jsonPath("$.balanceDays").value(2));
        org.assertj.core.api.Assertions.assertThat(statusInTheDatabase(id)).isEqualTo("PENDING");
    }

    @Test
    void malformedRequestsAre400() throws Exception {
        for (String body : new String[]{
                "{\"employeeId\":1,\"startDate\":\"2026-11-06\",\"endDate\":\"2026-11-10\"}",                 // no reason
                "{\"employeeId\":1,\"startDate\":\"2026-11-06\",\"reason\":\"Trip\"}",                        // no end date
                "{\"employeeId\":1,\"startDate\":\"06-11-2026\",\"endDate\":\"2026-11-10\",\"reason\":\"Trip\"}",   // not ISO
                "{\"startDate\":\"2026-11-06\",\"endDate\":\"2026-11-10\",\"reason\":\"Trip\"}"}) {            // no employee
            mvc.perform(post("/leave-requests").contentType(MediaType.APPLICATION_JSON).content(body)).andExpect(status().isBadRequest());
        }
    }

    @Test
    void impossibleRequestsAre422() throws Exception {
        ask(1, "2026-11-10", "2026-11-06").andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.title").value("Invalid dates"));
        ask(1, "2026-11-07", "2026-11-08").andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.title").value("No working days"));
        ask(1, "2026-11-02", "2026-12-14").andExpect(status().isUnprocessableContent());   // 43 calendar days: one too many
        ask(1, "2026-11-02", "2026-12-13").andExpect(status().isCreated()).andExpect(jsonPath("$.days").value(30));
        ask(99, "2026-11-06", "2026-11-10").andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.title").value("Unknown employee"));
    }

    @Test
    void unknownRequestsAndEmployeesAre404() throws Exception {
        approve(999).andExpect(status().isNotFound()).andExpect(jsonPath("$.detail").value("No leave request 999."));
        mvc.perform(get("/employees/99/leave-balance")).andExpect(status().isNotFound());
    }
}
