package com.bimaly.policies;

import com.bimaly.policies.insurer.IssuePolicyRequest;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.oxm.jaxb.Jaxb2Marshaller;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.ws.client.core.WebServiceTemplate;
import org.springframework.ws.soap.client.SoapFaultClientException;
import org.springframework.ws.transport.http.HttpUrlConnectionMessageSender;

import javax.xml.datatype.DatatypeFactory;
import java.time.Duration;
import java.util.concurrent.CompletableFuture;

import static com.bimaly.policies.TestInsurer.INSURER;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.awaitility.Awaitility.await;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The insurer is slow today, and it refuses some requests. Written first. */
class LegacySoapTrapTest extends ApiTest {

    @Autowired
    Jaxb2Marshaller messages;

    /** The old way: a WebServiceTemplate as it comes, and no handling of faults. */
    WebServiceTemplate oldClient() {
        WebServiceTemplate template = new WebServiceTemplate(messages);
        template.setDefaultUri(INSURER.url());
        return template;
    }

    static IssuePolicyRequest request(String product) {
        IssuePolicyRequest r = new IssuePolicyRequest();
        r.setCustomerName("Meera Iyer");
        r.setDateOfBirth(DatatypeFactory.newDefaultInstance().newXMLGregorianCalendar("1988-04-12"));
        r.setProductCode(product);
        r.setSumInsuredPaise(1_000_000_000L);
        return r;
    }

    @Test
    void theOldClientWaitsAsLongAsTheInsurerDoes() throws Exception {
        // Spring-WS's default sender gives the insurer 60 s to connect and 60 s more to answer.
        var sender = (HttpUrlConnectionMessageSender) oldClient().getMessageSenders()[0];
        assertThat(ReflectionTestUtils.getField(sender, "readTimeout")).isEqualTo(Duration.ofSeconds(60));

        INSURER.delayMillis = 4_000;
        var old = CompletableFuture.supplyAsync(() -> oldClient().marshalSendAndReceive(request("TERM10")));
        await().during(Duration.ofSeconds(2)).atMost(Duration.ofSeconds(3)).until(() -> !old.isDone());   // a request thread, held
        old.join();

        long started = System.nanoTime();
        issue("TERM10", 1_000_000_000L).andExpect(status().isGatewayTimeout());   // the API gives up after its 1 s
        assertThat((System.nanoTime() - started) / 1_000_000).isLessThan(2_000);
    }

    @Test
    void theOldWayLetsAFaultEscapeAsAnErrorAndTheApiExplainsIt() throws Exception {
        assertThatThrownBy(() -> oldClient().marshalSendAndReceive(request("CAR1")))
                .isInstanceOf(SoapFaultClientException.class);   // unhandled in a controller: a 500 with no reason
        issue("CAR1", 1_000_000_000L).andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.detail").value("The insurer refused the policy: Product CAR1 is not sold."))
                .andExpect(jsonPath("$.insurerCode").value("PRODUCT_UNKNOWN"));
    }
}
