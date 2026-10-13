package com.seatsure.registrations;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.not;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract: created, read back, and every way a registration can be refused. */
class RegistrationContractTest extends ApiTest {

    @Test
    void validRegistrationIs201WithLocationAndBody() throws Exception {
        register("pune-tech-summit-2026", asha())
                .andExpect(status().isCreated())
                .andExpect(header().string("Location", org.hamcrest.Matchers.matchesPattern(
                        "/events/pune-tech-summit-2026/registrations/[0-9a-f-]{36}")))
                .andExpect(jsonPath("$.id").isNotEmpty())
                .andExpect(jsonPath("$.eventId").value("pune-tech-summit-2026"))
                .andExpect(jsonPath("$.name").value("Asha Kulkarni"))
                .andExpect(jsonPath("$.email", org.hamcrest.Matchers.matchesPattern("asha\\.\\d+@example\\.com")))
                .andExpect(jsonPath("$.phone").value("9876543210"))
                .andExpect(jsonPath("$.tickets").value(2))
                .andExpect(jsonPath("$.registeredAt").isNotEmpty());
    }

    @Test
    void theRegistrationCanBeReadBackAtItsLocation() throws Exception {
        var created = register("pune-tech-summit-2026", asha()).andReturn().getResponse();
        mvc.perform(get(created.getHeader("Location")))
                .andExpect(status().isOk())
                .andExpect(content().json(created.getContentAsString()));
    }

    @Test
    void surroundingSpacesAreTrimmedAndABlankPhoneMeansNoPhone() throws Exception {
        register("goa-food-fest-2026", """
                {"name":"  Ravi Menon ","email":" ravi@example.com ","phone":"  ","tickets":1}
                """)
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.name").value("Ravi Menon"))
                .andExpect(jsonPath("$.email").value("ravi@example.com"))
                .andExpect(jsonPath("$.phone").isEmpty());
    }

    @Test
    void everyMissingFieldIsListed() throws Exception {
        int before = store.count();
        register("pune-tech-summit-2026", "{}")
                .andExpect(status().isBadRequest())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.detail").value("The registration has invalid fields."))
                .andExpect(jsonPath("$.errors.name").value("must not be blank"))
                .andExpect(jsonPath("$.errors.email").value("must not be blank"))
                .andExpect(jsonPath("$.errors.tickets").value("must not be null"))
                .andExpect(jsonPath("$.errors.phone").doesNotExist());
        assertThat(store.count()).isEqualTo(before);
    }

    @Test
    void moreThan10TicketsIs400() throws Exception {
        register("pune-tech-summit-2026", asha().replace("\"tickets\":2", "\"tickets\":11"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.tickets").value("at most 10 tickets per registration"));
    }

    @Test
    void aWrongPhoneIs400() throws Exception {
        register("pune-tech-summit-2026", asha().replace("9876543210", "12345"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.phone").value("must be a 10-digit mobile number"));
    }

    @Test
    void ticketsMustBeAWholeNumber() throws Exception {
        register("pune-tech-summit-2026", asha().replace("\"tickets\":2", "\"tickets\":2.5"))
                .andExpect(status().isBadRequest());
        register("pune-tech-summit-2026", asha().replace("\"tickets\":2", "\"tickets\":\"two\""))
                .andExpect(status().isBadRequest());
    }

    @Test
    void brokenOrMissingJsonIs400() throws Exception {
        register("pune-tech-summit-2026", "{\"name\":").andExpect(status().isBadRequest())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON));
        mvc.perform(post("/events/pune-tech-summit-2026/registrations").contentType(MediaType.APPLICATION_JSON))
                .andExpect(status().isBadRequest());
    }

    @Test
    void aFormPostInsteadOfJsonIs415() throws Exception {
        mvc.perform(post("/events/pune-tech-summit-2026/registrations")
                        .contentType(MediaType.APPLICATION_FORM_URLENCODED).content("name=Asha&tickets=2"))
                .andExpect(status().isUnsupportedMediaType());
    }

    @Test
    void theClientCannotChooseTheIdOrTheTime() throws Exception {
        String fixed = "00000000-0000-0000-0000-000000000001";
        register("pune-tech-summit-2026", asha().replace("{", "{\"id\":\"" + fixed + "\",\"registeredAt\":\"2020-01-01T00:00:00Z\","))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id", not(fixed)))
                .andExpect(jsonPath("$.registeredAt", not("2020-01-01T00:00:00Z")));
    }

    @Test
    void unknownEventIs404ForPostAndGet() throws Exception {
        register("mumbai-marathon-2026", asha())
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.title").value("Event not found"));
        mvc.perform(get("/events/mumbai-marathon-2026/registrations/{id}", UUID.randomUUID()))
                .andExpect(status().isNotFound());
    }

    @Test
    void unknownRegistrationIs404() throws Exception {
        mvc.perform(get("/events/pune-tech-summit-2026/registrations/{id}", UUID.randomUUID()))
                .andExpect(status().isNotFound())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.title").value("Registration not found"));
    }

    @Test
    void aRegistrationIsNotFoundUnderAnotherEvent() throws Exception {
        String location = register("pune-tech-summit-2026", asha()).andReturn().getResponse().getHeader("Location");
        mvc.perform(get(location.replace("pune-tech-summit-2026", "goa-food-fest-2026")))
                .andExpect(status().isNotFound());
    }

    @Test
    void aMalformedRegistrationIdIs400() throws Exception {
        mvc.perform(get("/events/pune-tech-summit-2026/registrations/not-a-uuid"))
                .andExpect(status().isBadRequest());
    }
}
