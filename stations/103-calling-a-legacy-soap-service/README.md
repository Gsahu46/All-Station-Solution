# Station 103 · Calling a legacy SOAP service

Working Systems · 0–2 years · Specialisation · Insurance · Types: none

Spring Boot 4.1.1 · Java 25 · Spring-WS 5 · JAXB classes generated from the WSDL · java.net.http client with timeouts. Needs JDK 25 (or 21, see Set up & code). No Docker and no database: the tests start their own simulated insurer. Python 3 runs the simulated insurer in Try it yourself. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** The insurer's SOAP service is simulated: a small server answers with SOAP envelopes written by hand (no policy is really issued). The customers and products are demo data.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 7 tests.

# 1 · Understand

## The problem in real life

1.  **The insurer's old system**

    Bimaly sells health and term insurance. Policies are issued only by the insurer's 15-year-old SOAP service. Nobody on the team had used SOAP.

2.  **A minute of waiting, then a 500**

    The first client used the library's defaults. On a slow day the insurer took 40 seconds; customers waited, retried and stacked up. When the insurer said "we do not sell that product", the customer saw "500 Internal Server Error".

3.  **The fix**

    The client is generated from the WSDL, gives the insurer 8 seconds at most, and reads each fault: our mistake is a 422 with the insurer's reason, the insurer's failure is a 502, and no answer is a 504 that says the policy may or may not exist.

Every call to another system needs a time limit and an honest translation of its errors. Old systems need both most.

## What are we building?

A JSON endpoint that issues a policy through the insurer's SOAP service, with time limits and clear errors.

## An everyday analogy

A travel agent booking with an airline that only accepts paper forms by fax. The agent fills in the airline's form exactly, waits a fixed time for the reply, and tells the customer in plain words whether the airline refused ("no seats in that class") or its fax machine is broken.

## How it works in 4 steps

1.  **Check**: the request is validated before anything is sent; a bad request never reaches the insurer.
2.  **Translate**: generated classes turn it into the insurer's XML envelope.
3.  **Send, with a limit**: at most 2 s to connect and 8 s for the answer.
4.  **Translate back**: a policy is `201`; a refusal `422`; the insurer failing `502`; no answer `504`.

Check yourself: why not retry when the insurer does not answer?

The insurer may have issued the policy and only the answer was lost. A retry could issue a second policy for the same person. The API says "may or may not have been issued" instead.

## What this station is not

- **No real insurer.** A small simulated SOAP server answers.
- **No database.** The insurer keeps the policies; we only pass them on.
- **No SOAP server of our own.** We only call one.

## Key terms

| Term                         | Simple meaning                                                                           | Everyday example                                           | In this project                     |
|------------------------------|------------------------------------------------------------------------------------------|------------------------------------------------------------|-------------------------------------|
| **SOAP**                     | An older way for systems to talk: every message is an XML "envelope" sent by HTTP POST.  | A letter in a fixed government form.                       | the insurer's IssuePolicy           |
| **WSDL**                     | An XML file that describes a SOAP service: its operations, its messages and its address. | The form's instruction booklet.                            | `policy-issuance.wsdl`              |
| **Generated client classes** | Java classes made from the WSDL at build time, so you never write the XML yourself.      | A pre-printed form you only fill in.                       | `IssuePolicyRequest`, `PolicyFault` |
| **SOAP fault**               | SOAP's error message: a code (whose mistake: Client or Server), a reason, and details.   | The form sent back with "rejected: field 4" stamped on it. | 422 or 502                          |
| **Timeout**                  | How long you wait for an answer before giving up.                                        | Hanging up after a minute on hold.                         | connect 2 s, answer 8 s             |
| **Circuit breaker**          | After several failures in a row, stop calling for a while.                               | Not redialling a number that is clearly down.              | challenge 2                         |

# 2 · Build: Spec

## Business problem

**Bimaly** (a fictional insurance broker) issues policies through its insurer's SOAP service. Slow answers hold requests for a minute, and refusals reach customers as 500s.

## Acceptance criteria

Demo rules: 2 s to connect, 8 s for the whole answer (the insurer usually answers in 1 to 3 s, at worst 6 s); a name of at most 100 characters; a product code of 3 to 10 letters or digits.

1.  **Given** a valid request the insurer accepts, **then** `201` with the insurer's policy number and premium, and a `Location`.
2.  **Given** a request the insurer refuses (a Client fault), **then** `422` with the insurer's reason and code.
3.  **Given** the insurer's own failure (a Server fault) or no connection, **then** `502`.
4.  **Given** no answer within 8 s, **then** `504`, saying the policy may or may not have been issued.
5.  **Given** bad input, **then** `400`, and nothing is sent.

## Requirements

- The client is generated from the insurer's WSDL, not written by hand.
- Every call has a connect timeout and an answer timeout.
- IssuePolicy is never retried automatically: it is not idempotent.

## Learning objectives

- Read a WSDL: operations, messages, faults, address.
- Generate client classes from it with Maven.
- Call a SOAP operation with Spring-WS and set real timeouts.
- Map SOAP faults to honest HTTP errors.
- Test against a simulated SOAP server, including slow and broken answers.

# 2 · Build: API contract

## Endpoints

| Method | Path        | Purpose                                                                      |
|--------|-------------|------------------------------------------------------------------------------|
| `POST` | `/policies` | Issue a policy: `{customerName, dateOfBirth, productCode, sumInsuredPaise}`. |

## Status codes

| Status | When                                                        |
|--------|-------------------------------------------------------------|
| 201    | Issued by the insurer                                       |
| 400    | Missing or bad fields; a date of birth not in the past      |
| 422    | The insurer refused the request (its code in `insurerCode`) |
| 502    | The insurer's system failed, or could not be reached        |
| 504    | No answer within 8 s; the policy may or may not exist       |

## Captured examples

Captured with curl from the running app on 24 Oct 2026, in this order, against `docs/test-insurer.py`, a small simulated insurer. `Date`, connection and standard security headers are left out.

### Case 1: a term policy

**Why:** `201`; the policy number comes from the insurer.

Request

``` code
POST /policies HTTP/1.1
Content-Type: application/json

{
  "customerName": "Meera Iyer",
  "dateOfBirth": "1988-04-12",
  "productCode": "TERM10",
  "sumInsuredPaise": 1000000000
}
```

Response

``` code
HTTP/1.1 201 
Location: /policies/SG-2026-000001
Content-Type: application/json

{
  "policyNumber": "SG-2026-000001",
  "productCode": "TERM10",
  "sumInsuredPaise": 1000000000,
  "premiumPaise": 1000000
}
```

### Case 2: a product the insurer does not sell

**Why:** a Client fault: `422` with the insurer's own reason.

Request

``` code
POST /policies HTTP/1.1
Content-Type: application/json

{
  "customerName": "Meera Iyer",
  "dateOfBirth": "1988-04-12",
  "productCode": "CAR1",
  "sumInsuredPaise": 1000000000
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "The insurer refused the policy: Product CAR1 is not sold.",
  "instance": "/policies",
  "status": 422,
  "title": "Unprocessable Content",
  "insurerCode": "PRODUCT_UNKNOWN"
}
```

### Case 3: a sum above the insurer's limit

**Why:** the insurer's rule, not ours: `422`.

Request

``` code
POST /policies HTTP/1.1
Content-Type: application/json

{
  "customerName": "Ravi Kumar",
  "dateOfBirth": "1975-11-02",
  "productCode": "HEALTH5",
  "sumInsuredPaise": 60000000000
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "The insurer refused the policy: The sum insured is above the limit for online issuance.",
  "instance": "/policies",
  "status": 422,
  "title": "Unprocessable Content",
  "insurerCode": "SUM_TOO_HIGH"
}
```

### Case 4: a date of birth in the future

**Why:** `400`; nothing sent.

Request

``` code
POST /policies HTTP/1.1
Content-Type: application/json

{
  "customerName": "Ravi Kumar",
  "dateOfBirth": "2999-01-01",
  "productCode": "HEALTH5",
  "sumInsuredPaise": 50000000
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Invalid request content.",
  "instance": "/policies",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 5: the insurer's system fails

**Why:** a Server fault: `502`, and no internal detail passed on.

Request

``` code
POST /policies HTTP/1.1
Content-Type: application/json

{
  "customerName": "Asha Rao",
  "dateOfBirth": "1990-06-30",
  "productCode": "HEALTH5",
  "sumInsuredPaise": 50000000
}
```

Response

``` code
HTTP/1.1 502 
Content-Type: application/problem+json

{
  "detail": "The insurer's system failed. Try again later.",
  "instance": "/policies",
  "status": 502,
  "title": "Bad Gateway"
}
```

### Case 6: the insurer hangs for 20 s

**Why:** `504` after 8 s.

Request

``` code
POST /policies HTTP/1.1
Content-Type: application/json

{
  "customerName": "Asha Rao",
  "dateOfBirth": "1990-06-30",
  "productCode": "HEALTH5",
  "sumInsuredPaise": 50000000
}
```

Response

``` code
HTTP/1.1 504 
Content-Type: application/problem+json

{
  "detail": "The insurer did not answer in time. The policy may or may not have been issued: check before trying again.",
  "instance": "/policies",
  "status": 504,
  "title": "Gateway Timeout"
}
```

How long case 6 took, measured by curl:

``` code
the app answered 504 after 8.010278 s (its limit: 8 s; the insurer would have taken 20 s)
```

## On the wire

What the simulated insurer received and sent back for cases 1 and 2. Note the `SOAPAction` header, and that SOAP 1.1 sends a fault with HTTP 500.

``` code
SOAPAction: "http://insurer.example/policy/v1/IssuePolicy"

<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"><SOAP-ENV:Header/><SOAP-ENV:Body><ns2:IssuePolicyRequest xmlns:ns2="http://insurer.example/policy/v1"><ns2:customerName>Meera Iyer</ns2:customerName><ns2:dateOfBirth>1988-04-12</ns2:dateOfBirth><ns2:productCode>TERM10</ns2:productCode><ns2:sumInsuredPaise>1000000000</ns2:sumInsuredPaise></ns2:IssuePolicyRequest></SOAP-ENV:Body></SOAP-ENV:Envelope>

--- answer (HTTP 200) ---

<?xml version="1.0" encoding="UTF-8"?><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><p:IssuePolicyResponse xmlns:p="http://insurer.example/policy/v1"><p:policyNumber>SG-2026-000001</p:policyNumber><p:premiumPaise>1000000</p:premiumPaise></p:IssuePolicyResponse></soap:Body></soap:Envelope>
```

``` code
SOAPAction: "http://insurer.example/policy/v1/IssuePolicy"

<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"><SOAP-ENV:Header/><SOAP-ENV:Body><ns2:IssuePolicyRequest xmlns:ns2="http://insurer.example/policy/v1"><ns2:customerName>Meera Iyer</ns2:customerName><ns2:dateOfBirth>1988-04-12</ns2:dateOfBirth><ns2:productCode>CAR1</ns2:productCode><ns2:sumInsuredPaise>1000000000</ns2:sumInsuredPaise></ns2:IssuePolicyRequest></SOAP-ENV:Body></SOAP-ENV:Envelope>

--- answer (HTTP 500) ---

<?xml version="1.0" encoding="UTF-8"?><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><soap:Fault><faultcode>soap:Client</faultcode><faultstring>Validation failed</faultstring><detail><p:PolicyFault xmlns:p="http://insurer.example/policy/v1"><p:code>PRODUCT_UNKNOWN</p:code><p:message>Product CAR1 is not sold.</p:message></p:PolicyFault></detail></soap:Fault></soap:Body></soap:Envelope>
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                              | What happens                                        | Proved by                                               |
|-----------------------------------|-----------------------------------------------------|---------------------------------------------------------|
| The old client and a slow insurer | 60 s read timeout; still waiting after 2 s          | `theOldClientWaitsAsLongAsTheInsurerDoes`               |
| The old way and a refusal         | An exception escapes (a 500); the API answers `422` | `theOldWayLetsAFaultEscapeAsAnErrorAndTheApiExplainsIt` |
| A policy issued                   | `201`, Location, SOAPAction sent                    | `aPolicyIsIssuedThroughTheInsurersSoapService`          |
| A refusal                         | `422` with the insurer's reason and code            | `theInsurersRefusalIs422WithItsReason`                  |
| A Server fault; a slow insurer    | `502`; `504`                                        | `theInsurersOwnFailureIs502AndASlowInsurer504`          |
| Bad input                         | `400`; the insurer gets nothing                     | `badRequestsAre400AndNeverReachTheInsurer`              |
| No insurer listening              | `502`                                               | `anInsurerThatCannotBeReachedIs502`                     |

## The trap

Plausible but wrong

No timeout on a slow legacy service, and SOAP faults turned into 500s.

- **The old way.** A `WebServiceTemplate` as it comes. Its default sender waits 60 s to connect and 60 s for an answer: the test reads the value and shows a request still waiting after 2 s. A refusal arrives as `SoapFaultClientException`; nothing catches it, so the customer gets a 500 with no reason.
- **The API.** Gives up after its limit (1 s in the tests) with `504`, and turns the same refusal into `422` "The insurer refused the policy: Product CAR1 is not sold."

While building, each part was undone once: no timeouts turned 2 tests red; no SOAPAction 1; every fault as `422` 1; the fault's detail ignored 2; every lost answer as `502` 2; the product code not upper-cased 1; no pattern on the product code 1.

``` code
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
```

# 2 · Build: Set up & code

## Set up and run

| You need | Version                                           | Check with          |
|----------|---------------------------------------------------|---------------------|
| JDK      | 25 (recommended). JDK 21 also works, see below    | `java -version`     |
| Python 3 | Only for the simulated insurer in Try it yourself | `python3 --version` |
| Maven    | Not needed: the project ships the Maven wrapper   |                     |

**macOS / Linux**

``` code
python3 docs/test-insurer.py 9088 &   # the simulated insurer
./mvnw spring-boot:run      # generates the client from the WSDL; the API on http://localhost:8080
./mvnw test                 # all 7 tests; they start their own simulated insurer
```

**Windows (PowerShell)**

``` code
Start-Process python -ArgumentList 'docs/test-insurer.py','9088'
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Make the insurer hang, then issue a policy:

``` code
curl -d '{"delay":20}' http://127.0.0.1:9088/control
curl -i -H 'Content-Type: application/json' -d '{"customerName":"Asha Rao","dateOfBirth":"1990-06-30","productCode":"HEALTH5","sumInsuredPaise":50000000}' localhost:8080/policies
```

The answer is `504` after 8 s. Then copy the Review tab's `PoliciesApplication.java` over the real one and try again: the request waits the full 20 s.

## Troubleshooting

| You see                                                   | Cause                                                               | Fix                                                                                                    |
|-----------------------------------------------------------|---------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------|
| `cannot find symbol IssuePolicyRequest` in the IDE        | The classes are generated by the build.                             | Run `./mvnw compile` once, and mark `target/generated-sources` as a source folder if the IDE does not. |
| `HttpClient is not available`                             | A `JdkHttpClientMessageSender` made by hand, without an HttpClient. | Pass one to its constructor, as in `PoliciesApplication`.                                              |
| The insurer answers "no operation" or ignores the request | No or wrong `SOAPAction` header.                                    | Send the action named in the WSDL's binding.                                                           |

## Project layout

``` tree
stations/103-calling-a-legacy-soap-service/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/bimaly/policies/
│   ├── PolicyController.java   ├── InsurerClient.java   └── PoliciesApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── wsdl/policy-issuance.wsdl
├── target/generated-sources/   com/bimaly/policies/insurer/ (made by the build)
├── src/test/java/com/bimaly/policies/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, simulated insurer, captures, saved runs
```

## Code walkthrough

The contract first, then in the order a request travels.

#### `src/main/resources/wsdl/policy-issuance.wsdl`

Does  
The insurer's contract.

Why  
One operation, IssuePolicy; its request, answer and fault; the address. SOAP 1.1, document/literal.

Without it  
Hand-written XML that drifts from what the insurer expects.

- Here a copy of the insurer's file, kept in the project so the build does not depend on their server.

#### `pom.xml`

Does  
Generating the client.

Why  
`jaxb-maven-plugin` reads the WSDL at build time and writes `com.bimaly.policies.insurer` into `target/`.

Without it  
Generated code checked in and forgotten when the WSDL changes.

#### `src/main/java/com/bimaly/policies/PolicyController.java`

Does  
The endpoint and its errors.

Why  
Validates, builds the generated request, and turns each outcome into one status with a plain sentence.

Without it  
A 500 for every problem on the insurer's side.

#### `src/main/java/com/bimaly/policies/InsurerClient.java`

Does  
The SOAP call.

Why  
Sends the SOAPAction; reads a fault's code (Client/Sender: our request; Server/Receiver: theirs) and its PolicyFault detail; tells a timeout from a lost connection.

Without it  
"The insurer refused" and "the insurer is broken" looking the same.

- A timeout is recognised by its cause (`HttpTimeoutException`), not by the words of its message.

#### `src/main/java/com/bimaly/policies/PoliciesApplication.java`

Does  
The client's settings.

Why  
`JdkHttpClientMessageSender`: connect 2 s, whole request 8 s.

Without it  
Spring-WS's default sender: 60 s and 60 s.

- Made inside a `@Bean` method, the sender must be given its `HttpClient`: it only builds one in `afterPropertiesSet`, which Spring calls for beans, and otherwise fails with "HttpClient is not available". Found while building.

#### `src/main/resources/application.yaml`

The insurer's address and the two timeouts.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                              | Test class                                      | Result |
|---------------|------------------------------------------|-------------------------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found | `PolicyContractTest` (4), `InsurerDownTest` (1) | pass   |
| Every station | Reproduce the failure before the fix     | `LegacySoapTrapTest` (2)                        | pass   |

"Not found" here is the insurer's side: a product it does not sell (`422`) and an insurer that cannot be reached (`502`); there is no policy to look up in this station. The tests' simulated insurer answers with hand-written SOAP 1.1 envelopes, can be made slow or broken, and the API's limit is 1 s, so a hang is reached in a second.

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 1, Failures: 0, Errors: 0, Skipped: 0 -- in com.bimaly.policies.InsurerDownTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.bimaly.policies.LegacySoapTrapTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.bimaly.policies.PolicyContractTest
[INFO] Tests run: 7, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/bimaly/policies/LegacySoapTrapTest.java`

Written first: the client as it comes against the API, a slow insurer and a refusal.

#### `src/test/java/com/bimaly/policies/PolicyContractTest.java`

Issued, refused, failed, slow and bad requests.

#### `src/test/java/com/bimaly/policies/InsurerDownTest.java`

Nothing listening at the insurer's address.

#### `src/test/java/com/bimaly/policies/TestInsurer.java`

A simulated SOAP service: hand-written envelopes, a delay, a broken switch, the requests it received.

#### `src/test/java/com/bimaly/policies/ApiTest.java`

Shared setup: the insurer's address and the 1 s limit.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/bimaly/policies/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=MaskedSoapLogChallengeTest`.
3.  Change the code until it passes, then run `./mvnw test` to check the other 7 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 11 tests pass (7 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## Log the envelopes, not the customer

When the insurer refuses something, support wants to see the exact XML. Log every request, answer and fault envelope at DEBUG on the logger `com.bimaly.policies.SoapLog`, with the customer's name replaced by `***`.

**Done when:** both tests in `MaskedSoapLogChallengeTest` pass.

Hints

- A Spring-WS `ClientInterceptor` sees each message: `handleRequest`, `handleResponse`, `handleFault`.
- Write the message to a `ByteArrayOutputStream`, then mask the `customerName` element.
- Register it with `template.setInterceptors(...)`, and return `true` so the call goes on.

#### `challenge/MaskedSoapLogChallengeTest.java`

``` code
package com.bimaly.policies;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.boot.test.system.CapturedOutput;
import org.springframework.boot.test.system.OutputCaptureExtension;
import org.springframework.test.context.TestPropertySource;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: when the insurer disputes a policy, support needs the exact envelopes. Log each request and response
 * envelope at DEBUG (logger com.bimaly.policies.SoapLog), with the customer's name replaced by ***.
 */
@ExtendWith(OutputCaptureExtension.class)
@TestPropertySource(properties = "logging.level.com.bimaly.policies.SoapLog=DEBUG")
class MaskedSoapLogChallengeTest extends ApiTest {

    @Test
    void envelopesAreLoggedWithoutTheCustomersName(CapturedOutput output) throws Exception {
        issue("TERM10", 1_000_000_000L).andExpect(status().isCreated());
        assertThat(output.getOut()).contains("IssuePolicyRequest").contains("customerName>***</").contains("IssuePolicyResponse")
                .doesNotContain("Meera Iyer");
    }

    @Test
    void faultsAreLoggedToo(CapturedOutput output) throws Exception {
        issue("CAR1", 1_000_000_000L).andExpect(status().isUnprocessableContent());
        assertThat(output.getOut()).contains("PRODUCT_UNKNOWN").doesNotContain("Meera Iyer");
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 35 minutes

## Leave a struggling insurer alone

When the insurer is down, every customer still waits for a timeout. After 3 failures in a row (Server faults or no answer), answer `503` "The insurer is having trouble. Try again in a minute." without calling it, for `bimaly.insurer.cool-down` (1 s in the test). A refusal is an answer, so it does not count.

**Done when:** both tests in `CircuitBreakerChallengeTest` pass.

Hints

- Count failures in a row; reset the count on any answer, refusals included.
- Remember when the circuit opened; after the cool-down, let a call through.
- Many requests at once: an `AtomicInteger` and a `volatile` time are enough here.

#### `challenge/CircuitBreakerChallengeTest.java`

``` code
package com.bimaly.policies;

import org.junit.jupiter.api.Test;
import org.springframework.test.context.TestPropertySource;

import static com.bimaly.policies.TestInsurer.INSURER;
import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: a struggling 15-year-old system should not get more traffic. After 3 failures in a row (Server faults,
 * timeouts, no connection), stop calling the insurer for bimaly.insurer.cool-down (1 s here) and answer 503 at once.
 * A refusal (Client fault) is the insurer working, not failing.
 */
@TestPropertySource(properties = "bimaly.insurer.cool-down=1s")
class CircuitBreakerChallengeTest extends ApiTest {

    @Test
    void afterThreeFailuresTheInsurerIsLeftAloneForAWhile() throws Exception {
        INSURER.broken = true;
        for (int i = 0; i < 3; i++) {
            issue("TERM10", 1_000_000_000L).andExpect(status().isBadGateway());
        }
        issue("TERM10", 1_000_000_000L).andExpect(status().isServiceUnavailable())
                .andExpect(jsonPath("$.detail").value("The insurer is having trouble. Try again in a minute."));
        assertThat(INSURER.calls).hasSize(3);   // the fourth never reached it

        INSURER.broken = false;
        await().atMost(java.time.Duration.ofSeconds(3)).until(() -> issue("TERM10", 1_000_000_000L).andReturn().getResponse().getStatus() == 201);
    }

    @Test
    void refusalsDoNotOpenTheCircuit() throws Exception {
        for (int i = 0; i < 4; i++) {
            issue("CAR1", 1_000_000_000L).andExpect(status().isUnprocessableContent());
        }
        issue("TERM10", 1_000_000_000L).andExpect(status().isCreated());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## What happened to the 504?

A customer got `504`: the policy may or may not have been issued. The insurer's WSDL has no "look up by our reference" operation, but its team says they could add one next quarter. Design what Bimaly does today and after: what reference you send with each IssuePolicy, where you record the attempt, who checks it and when, and what the customer is told meanwhile.

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the client as it comes, against a slow and a refusing simulated insurer.
2.  Generate the classes from the WSDL; call IssuePolicy with the SOAPAction.
3.  Set both timeouts on the sender.
4.  Map faults by code, with the insurer's detail, and lost answers by cause.

## Design alternatives and trade-offs

| Approach                                 | What it costs                                               | Verdict              |
|------------------------------------------|-------------------------------------------------------------|----------------------|
| Generated classes + Spring-WS            | A build plugin; regenerate when the WSDL changes.           | Chosen               |
| Hand-written XML strings                 | Easy to start; breaks silently on namespaces and escaping.  | Avoid                |
| JAX-WS (Jakarta XML Web Services) client | Also generated from the WSDL; a second stack beside Spring. | Fine too             |
| The library's default timeouts           | 60 s per call, or none at all with some senders.            | The trap             |
| Retry IssuePolicy on a timeout           | A second policy for the same person.                        | Not without a lookup |

## Database design

No database in this station: the insurer stores the policies, and Bimaly passes them on. Challenge 3 asks where a record of each attempt would belong.

**Transaction boundaries:** none of our own. One SOAP call is one attempt at the insurer; it is never repeated automatically.

# 3 · Go deeper: Production

## Real-world considerations

Timeouts from the insurer's figures  
Ask the insurer for its usual and worst answer times; set the limit a little above the worst. Here: usually 1 to 3 s, at worst 6 s, limit 8 s (demo rules).

A changing WSDL  
Keep the insurer's WSDL in the project and regenerate on purpose. A new optional field is harmless; a renamed one fails the build, which is where you want to find out.

Security  
Real partners usually want HTTPS with client certificates, or WS-Security headers. Both are set on the message sender or as interceptors; neither is simulated here.

Logs  
Envelopes carry personal data: log them masked (challenge 1), and never the full detail of a Server fault to the customer.

Watching it  
Count outcomes (issued, refused, failed, timed out) and how long calls take. A rising timeout count is the first sign the insurer is struggling.

# 3 · Go deeper: Interview

## Interview takeaways

What is a WSDL, and what do you do with it?

The service's contract: operations, messages, faults and address. You generate client classes from it at build time.

What is the SOAPAction header?

In SOAP 1.1, an HTTP header naming the operation. Many old servers route by it, so send the value the WSDL gives.

How do you map SOAP faults to HTTP?

By the fault code: Client/Sender means our request was wrong (4xx, with the reason); Server/Receiver means theirs failed (502).

What are Spring-WS's default timeouts?

The default HttpURLConnection sender waits 60 s to connect and 60 s to read. Set your own on the sender.

Should you retry a timed-out call?

Only if the operation is idempotent or you can look up what happened. Issuing a policy is neither here.

How do you test a SOAP client?

Against a simulated SOAP server that sends real envelopes, including faults, delays and nothing at all.

## Self-check rubric

| Area        | Meets the bar                      | Above the bar                                                            |
|-------------|------------------------------------|--------------------------------------------------------------------------|
| Correctness | All 7 tests pass.                  | You ran the flawed version and explained each failure.                   |
| SOAP        | Generated classes; the call works. | You can read the WSDL and the captured envelopes and explain every part. |
| Errors      | No 500s for the insurer's answers. | Refusals, failures and timeouts each with an honest status and sentence. |
| Timeouts    | Set.                               | Chosen from the insurer's figures, and proved by a test.                 |

# 3 · Go deeper: Review

## The pull request

A teammate "simplifies" the client: "the defaults are fine, and a fault means the insurer had a problem". Read both files and list every problem before opening the findings.

#### `review/PoliciesApplication.java`

``` code
package com.bimaly.policies;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.oxm.jaxb.Jaxb2Marshaller;
import org.springframework.ws.client.core.WebServiceTemplate;

@SpringBootApplication
public class PoliciesApplication {

    public static void main(String[] args) {
        SpringApplication.run(PoliciesApplication.class, args);
    }

    /** XML to and from the classes generated from the insurer's WSDL at build time. */
    @Bean
    Jaxb2Marshaller insurerMessages() {
        Jaxb2Marshaller marshaller = new Jaxb2Marshaller();
        marshaller.setContextPath("com.bimaly.policies.insurer");
        return marshaller;
    }

    /** The SOAP client. Spring-WS's defaults are fine for a partner we trust. */
    @Bean
    WebServiceTemplate insurer(Jaxb2Marshaller messages, @Value("${bimaly.insurer.url}") String url) {
        WebServiceTemplate template = new WebServiceTemplate(messages);
        template.setDefaultUri(url);
        return template;
    }
}
```

#### `review/InsurerClient.java`

``` code
package com.bimaly.policies;

import com.bimaly.policies.insurer.IssuePolicyRequest;
import com.bimaly.policies.insurer.IssuePolicyResponse;
import com.bimaly.policies.insurer.PolicyFault;
import org.springframework.oxm.jaxb.Jaxb2Marshaller;
import org.springframework.stereotype.Component;
import org.springframework.ws.client.WebServiceIOException;
import org.springframework.ws.client.core.WebServiceTemplate;
import org.springframework.ws.soap.SoapFaultDetailElement;
import org.springframework.ws.soap.client.SoapFaultClientException;
import org.springframework.ws.soap.client.core.SoapActionCallback;

import java.io.IOException;
import java.net.http.HttpTimeoutException;
import java.util.Iterator;
import java.util.Set;

/** Calls the insurer's IssuePolicy operation and turns what can go wrong into three plain outcomes. */
@Component
class InsurerClient {

    static final String SOAP_ACTION = "http://insurer.example/policy/v1/IssuePolicy";

    /** The insurer answered with a SOAP fault. Its own fault code and message, and whose mistake it says it is. */
    static final class Refused extends RuntimeException {
        final boolean ourRequest;
        final String code;

        Refused(boolean ourRequest, String code, String message) {
            super(message);
            this.ourRequest = ourRequest;
            this.code = code;
        }
    }

    /** No answer: the insurer could not be reached, or did not answer in time. */
    static final class Unreachable extends RuntimeException {
        final boolean timedOut;

        Unreachable(boolean timedOut, Throwable cause) {
            super(cause);
            this.timedOut = timedOut;
        }
    }

    // SOAP 1.1 says Client and Server; SOAP 1.2 says Sender and Receiver.
    private static final Set<String> OUR_FAULT = Set.of("Client", "Sender");
    private final WebServiceTemplate insurer;
    private final Jaxb2Marshaller messages;

    InsurerClient(WebServiceTemplate insurer, Jaxb2Marshaller messages) {
        this.insurer = insurer;
        this.messages = messages;
    }

    IssuePolicyResponse issue(IssuePolicyRequest request) {
        try {
            return (IssuePolicyResponse) insurer.marshalSendAndReceive(request, new SoapActionCallback(SOAP_ACTION));
        } catch (SoapFaultClientException fault) {
            PolicyFault detail = detail(fault);
            boolean ours = false;   // a fault comes from the insurer, so it is the insurer's problem
            throw new Refused(ours, detail == null ? fault.getFaultCode().getLocalPart() : detail.getCode(),
                    detail == null ? fault.getFaultStringOrReason() : detail.getMessage());
        } catch (WebServiceIOException noAnswer) {
            boolean timedOut = false;
            for (Throwable t = noAnswer; t != null; t = t.getCause()) {
                timedOut |= t instanceof HttpTimeoutException;
            }
            throw new Unreachable(timedOut, noAnswer);
        }
    }

    /** The PolicyFault the WSDL declares, if the insurer sent one in the fault's detail. */
    private PolicyFault detail(SoapFaultClientException fault) {
        if (fault.getSoapFault().getFaultDetail() == null) {
            return null;
        }
        Iterator<SoapFaultDetailElement> entries = fault.getSoapFault().getFaultDetail().getDetailEntries();
        try {
            return entries.hasNext() && messages.unmarshal(entries.next().getSource()) instanceof PolicyFault p ? p : null;
        } catch (RuntimeException notOurs) {
            return null;
        }
    }
}
```

## Findings

1The library's default timeouts

"Spring-WS's defaults are fine for a partner we trust": the default sender waits 60 s to connect and 60 s for an answer. On a slow day each customer's request is held for up to two minutes, and the API's 8 s promise is gone.

**Test evidence:** `theOldClientWaitsAsLongAsTheInsurerDoes` and `theInsurersOwnFailureIs502AndASlowInsurer504` fail.

2Every fault is the insurer's problem

"A fault comes from the insurer, so it is the insurer's problem": a Client fault says our request was wrong. Answering `502` "try again later" makes the customer retry a request that can never succeed, and hides the reason the insurer gave.

**Test evidence:** `theInsurersRefusalIs422WithItsReason` and `theOldWayLetsAFaultEscapeAsAnErrorAndTheApiExplainsIt` fail.

## Same tests, flawed version

From `docs/review-run.txt`: the flawed files copied over the real ones, then the full suite run.

| Test class           | Fixed version | Flawed version |
|----------------------|---------------|----------------|
| `InsurerDownTest`    | 1 / 1         | 1 / 1          |
| `LegacySoapTrapTest` | 2 / 2         | 0 / 2          |
| `PolicyContractTest` | 4 / 4         | 2 / 4          |

On a good day, with a fast insurer and correct requests, the flawed version works. It fails on the slow day and on the first refusal.
