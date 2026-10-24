package com.bimaly.integration;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.json.JsonMapper;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class IntegrationRunContractTest extends ApiTest {

    @Test
    void aFileIsCheckedAndItsValidLinesQueued() throws Exception {
        upload("koshbank-20261001.csv", HEADER + """
                kb-1001,Meera Iyer,1988-04-12,term10,1000000000
                KB-1002,Ravi Kumar,1975-11-02,HEALTH5,50000000
                KB-1003,Asha Rao,1990-06-30,HEALTH5,50000000
                """);
        Runs.Run run = awaitRun("koshbank-20261001.csv", Runs.Status.DONE);

        mvc.perform(get("/integration/runs/{id}", run.id)).andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("DONE")).andExpect(jsonPath("$.file").value("koshbank-20261001.csv"))
                .andExpect(jsonPath("$.lines").value(3)).andExpect(jsonPath("$.accepted").value(3))
                .andExpect(jsonPath("$.rejected").isEmpty()).andExpect(jsonPath("$.checksum").isString());
        var messages = drain();
        assertThat(ids(messages)).containsExactly("KOSHBANK:KB-1001", "KOSHBANK:KB-1002", "KOSHBANK:KB-1003");
        var first = JsonMapper.builder().build().readTree(messages.getFirst().getBody());
        assertThat(first.path("productCode").asString()).isEqualTo("TERM10");
        assertThat(first.path("sumInsuredPaise").asLong()).isEqualTo(1_000_000_000L);
        assertThat(first.path("dateOfBirth").asString()).isEqualTo("1988-04-12");
    }

    @Test
    void badLinesAreRejectedWithTheirReasonAndTheOthersGoOn() throws Exception {
        upload("KOSHBANK-20261002.csv", HEADER + """
                KB-2001,Meera Iyer,1988-04-12,TERM10,1000000000
                KB-2002,Ravi Kumar,1975-11-02,HEALTH5
                KB-2003,Asha Rao,2999-01-01,HEALTH5,50000000
                KB-2004,Asha Rao,1990-06-30,HEALTH5,-5
                kb-2001,Meera Iyer,1988-04-12,TERM10,1000000000
                """);
        Runs.Run run = awaitRun("KOSHBANK-20261002.csv", Runs.Status.DONE);

        assertThat(run.lines).isEqualTo(5);
        assertThat(run.accepted).isEqualTo(1);
        assertThat(run.rejected).containsExactly(
                new PolicyFile.Rejected(3, "KB-2002", "expected 5 columns, found 4"),
                new PolicyFile.Rejected(4, "KB-2003", "the date of birth must be in the past"),
                new PolicyFile.Rejected(5, "KB-2004", "the sum insured must be 1 to 1000000000000 paise"),
                new PolicyFile.Rejected(6, "KB-2001", "reference KB-2001 already appears on line 2"));
        assertThat(ids(drain())).isEqualTo(List.of("KOSHBANK:KB-2001"));
    }

    @Test
    void anUnknownRunIs404AndANonNumberIs400() throws Exception {
        mvc.perform(get("/integration/runs/{id}", 999_999)).andExpect(status().isNotFound());
        mvc.perform(get("/integration/runs/{id}", "latest")).andExpect(status().isBadRequest());
        mvc.perform(get("/integration/runs/")).andExpect(status().isNotFound());
    }
}
