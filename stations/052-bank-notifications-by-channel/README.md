# Station 052 · Bank notifications by channel

Foundations · 0–1 years · Core · Fintech · Types: none

Spring Boot 4.1.1 · Java 25 · interfaces and constructor injection of List\<Channel\> · @MockitoSpyBean · Clock with @TestBean · RFC 9457 problem details. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Customers and messages are demo data, not Tijori's. No SMS, email or push is sent: each channel records the message in an in-memory outbox (a record is created). Which channel each notice must use is a demo rule, not a regulator's.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 10 tests.

# 1 · Understand

## The problem in real life

1.  **900 lines, three channels**

    Tijori's NotificationService wrote and sent SMS, email and push in one class. Every change was made in the same file.

2.  **Two email changes broke SMS**

    In March the email redesign lower-cased the address (customers without email now crashed before their SMS) and changed "Rs" to "₹" in the shared amount format (SMS lost its 160-character limit).

3.  **The fix**

    One small class per channel, each with its own wording and limits, behind a two-method interface; the service only decides which channels to use, and one channel's failure cannot stop another.

When three things change for different reasons, keep them in three places, so a change to one cannot break the others.

## What are we building?

Internal systems post a notice (`POST /notifications`): a debit, a new-device login, a statement. The service decides which channels it goes to and answers what happened on each. Customers set which channels they want (`PUT /customers/{id}/notification-preferences`).

## An everyday analogy

A bank branch with one clerk who writes every letter, SMS and phone call. Teach them a new letter format and they start writing SMS like letters. A branch with a letter desk, an SMS desk and a phone desk, and a manager who only says "send this to the SMS desk and the letter desk", can retrain one desk without the others noticing.

## How it works in 4 steps

1.  **A notice arrives**: debit of ₹1,499 for Asha at BigBasket.
2.  **The service asks the rule** for that type and Asha's preferences: which channels?
3.  **Each chosen channel** writes its own text and records it; a channel with no address says UNREACHABLE.
4.  **A channel that throws** is marked FAILED; the others are unaffected.

Check yourself: why does the SMS say "Rs" while the email says "₹"?

"₹" is not in GSM-7. One such character turns the whole SMS into UCS-2, where one part holds 70 characters instead of 160, so the alert costs two or three parts. Email has no such limit. Only the SMS class needs to know this.

## What this station is not

- **No real providers.** Messages are recorded, not sent.
- **No retries or queue.** Retrying failed channels is challenge 2.
- **No login.** In a bank only internal systems may post notices.

## Key terms

| Term                      | Simple meaning                                                     | Everyday example                                          | In this project                             |
|---------------------------|--------------------------------------------------------------------|-----------------------------------------------------------|---------------------------------------------|
| **Single responsibility** | A class has one reason to change.                                  | The SMS team edits SMS wording without touching email.    | `SmsChannel`, `EmailChannel`, `PushChannel` |
| **Interface**             | A promise of what a class can do, without saying how.              | "Can deliver a notice".                                   | `Channel`                                   |
| **Dependency inversion**  | The main logic depends on the promise, not on each concrete class. | The bank's rules call "a channel", not "the SMS gateway". | `NotificationService(List<Channel>)`        |
| **Failure isolation**     | One part failing does not stop the others.                         | The email server is down; the SMS still goes.             | `try` per channel                           |
| **GSM-7**                 | The alphabet an ordinary 160-character SMS uses.                   | "Rs" fits; "₹" does not.                                  | `SmsChannel`                                |
| **Overkill**              | Structure that costs more than it saves.                           | A factory of factories for three channels.                | Two-method interface, nothing more          |

# 2 · Build: Spec

## Business problem

**Tijori** (a fictional digital bank) sends alerts by SMS, email and push from one large class. Each change for one channel risked the others, and in March two of them stopped debit alerts.

## Acceptance criteria

1.  **Given** a ₹1,499 debit for Asha, **then** SMS, email and push are SENT, each in its own words; the SMS is GSM-7 and at most 160 characters.
2.  **Given** the same for Rohan (no email, no app), **then** the SMS is SENT, email UNREACHABLE, push SKIPPED.
3.  **Given** the email provider throws, **then** email is FAILED and SMS and push are SENT.
4.  **Given** Asha turns off email and push, **then** a statement notice goes by SMS only, a debit by SMS, and a new-device login still to all three.
5.  **Given** ₹1,23,45,678.90, **then** the SMS shows Indian grouping.
6.  **Given** a malformed body, `400`; a debit without amount or an unknown customer, `422`; preferences of an unknown customer, `404`.

## Requirements

- One class per channel; the service depends only on the `Channel` interface.
- One channel's failure never stops another.
- Money in integer paise, shown in Indian grouping.
- Addresses are masked in responses.

## Learning objectives

- Split a class by its reasons to change.
- Depend on a small interface and let Spring inject every implementation.
- Isolate failures between independent parts.
- Tell useful structure from overkill.

# 2 · Build: API contract

## Endpoints

| Method | Path                                       | Purpose                                                                                                                                                                                      |
|--------|--------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `POST` | `/notifications`                           | A notice: `customerId`, `type` (`DEBIT_ALERT`, `NEW_DEVICE_LOGIN`, `STATEMENT_READY`), `amountPaise` (debits), `merchant` (optional, up to 24 characters). Answers one delivery per channel. |
| `PUT`  | `/customers/{id}/notification-preferences` | Set `sms`, `email` and `push`, all three required.                                                                                                                                           |

## Delivery statuses

| Status        | Meaning                                                                        |
|---------------|--------------------------------------------------------------------------------|
| `SENT`        | The channel recorded the message (simulated sending).                          |
| `SKIPPED`     | The rule for this type and the customer's preferences do not use this channel. |
| `UNREACHABLE` | No address on this channel: no email on file, no app.                          |
| `FAILED`      | The channel threw; the others were still tried.                                |

## Status codes

| Status | When                                                                                         |
|--------|----------------------------------------------------------------------------------------------|
| 201    | Notice handled, whatever each channel's outcome                                              |
| 200    | Preferences saved                                                                            |
| 400    | Malformed body: missing customer, unknown type, amount 0 or with decimals, merchant too long |
| 404    | No such customer (preferences)                                                               |
| 422    | Unknown customer in the body; a debit alert without an amount                                |

## Captured examples

Captured with curl from the running app on 16 Oct 2026, in this order. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: a ₹1,499 debit for Asha

**Why:** three channels, three wordings; "Rs" in the SMS, "₹" elsewhere.

Request

``` code
POST /notifications HTTP/1.1
Content-Type: application/json

{
  "customerId": 1,
  "type": "DEBIT_ALERT",
  "amountPaise": 149900,
  "merchant": "BigBasket"
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 528

{
  "id": 1,
  "customerId": 1,
  "type": "DEBIT_ALERT",
  "deliveries": [
    {
      "channel": "SMS",
      "status": "SENT",
      "to": "******3210",
      "text": "Tijori: Rs 1,499.00 debited from a/c XX4821 at BIGBASKET on 16-10-26. Not you? Call 1800-000-0000."
    },
    {
      "channel": "EMAIL",
      "status": "SENT",
      "to": "a***@example.in",
      "text": "Subject: ₹1,499.00 debited\n\nDear Asha Verma,\n₹1,499.00 was debited from your account ending 4821 at BIGBASKET on 16 October 2026."
    },
    {
      "channel": "PUSH",
      "status": "SENT",
      "to": "this customer's app",
      "text": "₹1,499.00 debited at BIGBASKET"
    }
  ]
}
```

### Case 2: the same for Rohan

**Why:** no email: UNREACHABLE, and the SMS still goes. This is the case the old class crashed on.

Request

``` code
POST /notifications HTTP/1.1
Content-Type: application/json

{
  "customerId": 2,
  "type": "DEBIT_ALERT",
  "amountPaise": 149900,
  "merchant": "BigBasket"
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 344

{
  "id": 2,
  "customerId": 2,
  "type": "DEBIT_ALERT",
  "deliveries": [
    {
      "channel": "SMS",
      "status": "SENT",
      "to": "******6780",
      "text": "Tijori: Rs 1,499.00 debited from a/c XX7730 at BIGBASKET on 16-10-26. Not you? Call 1800-000-0000."
    },
    {
      "channel": "EMAIL",
      "status": "UNREACHABLE",
      "to": null,
      "text": null
    },
    {
      "channel": "PUSH",
      "status": "SKIPPED",
      "to": null,
      "text": null
    }
  ]
}
```

### Case 3: Asha keeps SMS only

**Why:** `200`.

Request

``` code
PUT /customers/1/notification-preferences HTTP/1.1
Content-Type: application/json

{
  "sms": true,
  "email": false,
  "push": false
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 39

{
  "sms": true,
  "email": false,
  "push": false
}
```

### Case 4: her statement notice

**Why:** statements follow preferences: SMS only.

Request

``` code
POST /notifications HTTP/1.1
Content-Type: application/json

{
  "customerId": 1,
  "type": "STATEMENT_READY"
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 304

{
  "id": 3,
  "customerId": 1,
  "type": "STATEMENT_READY",
  "deliveries": [
    {
      "channel": "SMS",
      "status": "SENT",
      "to": "******3210",
      "text": "Tijori: your statement for a/c XX4821 is ready in the app."
    },
    {
      "channel": "EMAIL",
      "status": "SKIPPED",
      "to": null,
      "text": null
    },
    {
      "channel": "PUSH",
      "status": "SKIPPED",
      "to": null,
      "text": null
    }
  ]
}
```

### Case 5: a debit of ₹1,23,45,678.90

**Why:** Indian grouping; still by SMS, whatever the preference.

Request

``` code
POST /notifications HTTP/1.1
Content-Type: application/json

{
  "customerId": 1,
  "type": "DEBIT_ALERT",
  "amountPaise": 1234567890,
  "merchant": "Sunrise Motors"
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 351

{
  "id": 4,
  "customerId": 1,
  "type": "DEBIT_ALERT",
  "deliveries": [
    {
      "channel": "SMS",
      "status": "SENT",
      "to": "******3210",
      "text": "Tijori: Rs 1,23,45,678.90 debited from a/c XX4821 at SUNRISE MOTORS on 16-10-26. Not you? Call 1800-000-0000."
    },
    {
      "channel": "EMAIL",
      "status": "SKIPPED",
      "to": null,
      "text": null
    },
    {
      "channel": "PUSH",
      "status": "SKIPPED",
      "to": null,
      "text": null
    }
  ]
}
```

### Case 6: a debit alert with no amount

**Why:** `422`.

Request

``` code
POST /notifications HTTP/1.1
Content-Type: application/json

{
  "customerId": 1,
  "type": "DEBIT_ALERT"
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "A debit alert needs amountPaise.",
  "instance": "/notifications",
  "status": 422,
  "title": "Amount missing"
}
```

### Case 7: type LOAN_OFFER

**Why:** not a notice this service sends: `400`.

Request

``` code
POST /notifications HTTP/1.1
Content-Type: application/json

{
  "customerId": 1,
  "type": "LOAN_OFFER"
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Failed to read request",
  "instance": "/notifications",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 8: preferences of customer 99

**Why:** `404`.

Request

``` code
PUT /customers/99/notification-preferences HTTP/1.1
Content-Type: application/json

{
  "sms": true,
  "email": true,
  "push": true
}
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No customer 99.",
  "instance": "/customers/99/notification-preferences",
  "status": 404,
  "title": "Customer not found"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                      | What happens                                                | Proved by                                                                 |
|-------------------------------------------|-------------------------------------------------------------|---------------------------------------------------------------------------|
| A debit for a customer with every channel | Three deliveries, each in its own words                     | `aDebitAlertGoesToEveryChannelInItsOwnWords`                              |
| Preferences off, by type                  | Statement by preference; debit always SMS; login everywhere | `preferencesDecideExceptWhereTheRulesSayOtherwise`                        |
| Lakhs and crores                          | Indian grouping                                             | `lakhsAndCroresAreGroupedTheIndianWay`, `rupeesAreGroupedInThreeThenTwos` |
| Email provider throws                     | Email FAILED, SMS and push SENT                             | `anEmailOutageLeavesSmsAndPushWorking`                                    |
| Malformed bodies                          | `400`, nothing recorded                                     | `brokenRequestsAre400`                                                    |
| Debit without amount; unknown customer    | `422`                                                       | `impossibleNoticesAre422`                                                 |
| Preferences of an unknown customer        | `404`                                                       | `unknownCustomersPreferencesAre404`                                       |

## The trap

Plausible but wrong

One class doing SMS, email and push, so one change breaks all three.

The old class is kept in the tests as `OldNotificationService`, with its two March changes. Both were made for email. The first lower-cases the email address before anything is sent: for Rohan, who has no email, it throws, and his debit alert never goes out by any channel. The second changed the shared amount format from "Rs" to "₹": the SMS now contains a character outside GSM-7 and is over 70 characters, so it is sent in parts. Through the fixed service, Rohan's SMS is SENT and Asha's SMS is GSM-7 within 160 characters.

While building, each part was undone once. Removing the per-channel `try` turned 1 test red (the email outage); "₹" in the SMS, 3; ignoring preferences, 1; western grouping, 2. Removing the email channel's "no address" check turned 1 red, and showed isolation working: the email channel threw, was marked FAILED instead of UNREACHABLE, and the SMS still went.

``` code
package com.tijori.notifications;

import org.junit.jupiter.api.Test;

import java.time.LocalDate;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * The first test written for this station: two changes made for email, in the one class that did all three
 * channels, and what they did to SMS. Then the same debit alert through the fixed service.
 */
class OneClassForAllChannelsTrapTest extends ApiTest {

    final Model.Notice debit = new Model.Notice(Model.NotificationType.DEBIT_ALERT, 149900L, "BIGBASKET", LocalDate.of(2026, 10, 16));

    @Test
    void anEmailChangeStopsTheSmsForCustomersWithoutEmail() throws Exception {
        Model.Customer rohan = customers.find(2).orElseThrow();
        assertThatThrownBy(() -> new OldNotificationService(outbox).notify(rohan, debit)).isInstanceOf(NullPointerException.class);
        assertThat(outbox.all()).isEmpty();   // Rohan's ₹1,499 debit alert never left: no SMS at all

        notify(debit(2, 149900)).andExpect(status().isCreated())
                .andExpect(jsonPath(statusOf("SMS")).value("SENT"))
                .andExpect(jsonPath(statusOf("EMAIL")).value("UNREACHABLE"))
                .andExpect(jsonPath(statusOf("PUSH")).value("SKIPPED"));
    }

    @Test
    void aRupeeSignForEmailTakesTheSmsOutOfGsm7() throws Exception {
        new OldNotificationService(outbox).notify(customers.find(1).orElseThrow(), debit);
        String oldSms = outbox.all().stream().filter(s -> s.channel() == Model.ChannelName.SMS).findFirst().orElseThrow().text();
        assertThat(oldSms).contains("₹").doesNotMatch(GSM7_SUBSET);   // sent as UCS-2: 70 characters a part, so 2 parts
        assertThat(oldSms.length()).isGreaterThan(70);

        outbox.clear();
        notify(debit(1, 149900));
        String sms = outbox.all().stream().filter(s -> s.channel() == Model.ChannelName.SMS).findFirst().orElseThrow().text();
        assertThat(sms).matches(GSM7_SUBSET).hasSizeLessThanOrEqualTo(SmsChannel.MAX_LENGTH);
    }
}
```

``` code
package com.tijori.notifications;

import java.time.format.DateTimeFormatter;

/**
 * The service as it shipped (900 lines in the original; the parts that matter here), kept only in tests. One class
 * writes and sends all three channels, in order, with one shared amount format.
 */
class OldNotificationService {

    private final Outbox outbox;

    OldNotificationService(Outbox outbox) {
        this.outbox = outbox;
    }

    /** Changed in March for the email redesign: "Rs" became "₹". Every channel uses it. */
    static String amount(long paise) {
        return "₹" + Rupees.format(paise);
    }

    void notify(Model.Customer c, Model.Notice n) {
        // Email first. Also changed in March: the new email provider wants lower-case addresses.
        String email = c.email().toLowerCase();
        outbox.record(Model.ChannelName.EMAIL, email, "Dear " + c.name() + ", " + amount(n.amountPaise()) + " was debited.");
        outbox.record(Model.ChannelName.SMS, c.phone(), "Tijori: " + amount(n.amountPaise()) + " debited from a/c XX" + c.accountLast4()
                + " at " + n.merchant() + " on " + DateTimeFormatter.ofPattern("dd-MM-yy").format(n.date()) + ". Not you? Call 1800-000-0000.");
        if (c.pushToken() != null) {
            outbox.record(Model.ChannelName.PUSH, c.pushToken(), amount(n.amountPaise()) + " debited");
        }
    }
}
```

# 2 · Build: Set up & code

## Set up and run

| You need | Version                                         | Check with      |
|----------|-------------------------------------------------|-----------------|
| JDK      | 25 (recommended). JDK 21 also works, see below  | `java -version` |
| Maven    | Not needed: the project ships the Maven wrapper |                 |
| Docker   | Not needed for this station                     |                 |

**macOS / Linux**

``` code
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all 10 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Change "Tijori: Rs " to "Tijori: ₹" in `SmsChannel` and run the tests:

``` code
./mvnw test -Dtest=OneClassForAllChannelsTrapTest
```

The GSM-7 test fails, and only for SMS: email and push are separate classes and do not change. Put it back.

## Troubleshooting

| You see                               | Cause                                                                                    | Fix                                                |
|---------------------------------------|------------------------------------------------------------------------------------------|----------------------------------------------------|
| An SMS billed as two or three parts   | A character outside GSM-7 (₹, curly quotes, emoji) makes it UCS-2: 70 characters a part. | Keep SMS text in GSM-7.                            |
| `12,345,678.00` for an Indian amount  | `DecimalFormat` has one grouping size.                                                   | Group the last three digits, then twos (`Rupees`). |
| One provider outage stops all alerts  | Channels called in a row without isolation.                                              | Catch per channel; record FAILED; carry on.        |
| `No qualifying bean of type Channel`  | A channel class without `@Component`, or outside the scanned package.                    | Annotate it in this package.                       |
| Channel order changes in the response | Spring's list order is not a contract.                                                   | Sort deliveries; tests look channels up by name.   |

## Project layout

``` tree
stations/052-bank-notifications-by-channel/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/tijori/notifications/
│   ├── NotificationController.java   ├── NotificationService.java   ├── Channel.java
│   ├── SmsChannel.java   ├── EmailChannel.java   ├── PushChannel.java
│   ├── Model.java   ├── Rupees.java   ├── Customers.java   ├── Outbox.java   └── NotificationsApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/tijori/notifications/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then each channel.

#### `src/main/java/com/tijori/notifications/NotificationController.java`

Does  
Validates the body, finds the customer, builds the channel-neutral notice.

Why  
HTTP only.

Without it  
Channel details in the controller.

#### `src/main/java/com/tijori/notifications/NotificationService.java`

Does  
Picks channels by the type's rule and the preferences; asks each to deliver; isolates failures.

Why  
Knows no wording and no provider: only the `Channel` interface.

Without it  
One channel's crash stopping the rest.

- Spring injects every `Channel` bean as a list: a new channel is a new class, not an edit here.
- A `RuntimeException` from one channel becomes FAILED for that channel only, and is logged.

#### `src/main/java/com/tijori/notifications/Channel.java`

Does  
Two methods: a name and `deliver`.

Why  
Small enough that every channel can honour it fully.

Without it  
A wide interface half of whose methods each channel fakes.

#### `src/main/java/com/tijori/notifications/SmsChannel.java`

Does  
SMS wording; GSM-7, 160 characters; masked phone.

Why  
The only place that knows SMS limits.

Without it  
"₹" in an SMS.

#### `src/main/java/com/tijori/notifications/EmailChannel.java`

Email subject and body; lower-cases the address only when there is one.

#### `src/main/java/com/tijori/notifications/PushChannel.java`

A short lock-screen line, with no account digits.

#### `src/main/java/com/tijori/notifications/Model.java`

The shared plain types; the per-type channel rule lives on `NotificationType`.

#### `src/main/java/com/tijori/notifications/Rupees.java`

Indian grouping for paise, written by hand because `DecimalFormat` supports only one group size.

#### `src/main/java/com/tijori/notifications/Customers.java`

Demo customers and their preferences, in memory.

#### `src/main/java/com/tijori/notifications/Outbox.java`

Where simulated sending records each message.

#### `src/main/java/com/tijori/notifications/NotificationsApplication.java`

Entry point; a `Clock` in India time for message dates.

# 2 · Build: Tests

## Required tests for this station

| Required by             | Requirement                                     | Test class                           | Result |
|-------------------------|-------------------------------------------------|--------------------------------------|--------|
| Every station           | HTTP contract: valid, invalid, not found        | `NotificationContractTest` (6)       | pass   |
| Every station           | Reproduce the failure before the fix            | `OneClassForAllChannelsTrapTest` (2) | pass   |
| This station's concepts | A channel failing alone; money formatting alone | `ChannelIsolationTest` (2)           | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 6, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.notifications.NotificationContractTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.notifications.ChannelIsolationTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.notifications.OneClassForAllChannelsTrapTest
[INFO] Tests run: 10, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/tijori/notifications/OneClassForAllChannelsTrapTest.java`

Written first: both March changes in the old class, then the fixed service.

#### `src/test/java/com/tijori/notifications/NotificationContractTest.java`

Wording per channel, preferences by type, Indian grouping, and every refusal.

#### `src/test/java/com/tijori/notifications/ChannelIsolationTest.java`

The email channel made to throw with `@MockitoSpyBean`; rupee grouping edge values.

#### `src/test/java/com/tijori/notifications/OldNotificationService.java`

The old class, kept only in tests.

#### `src/test/java/com/tijori/notifications/ApiTest.java`

Shared setup: a fixed Clock, an empty outbox and default preferences before each test.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/tijori/notifications/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=WhatsAppChallengeTest`.
3.  Change the code until it passes, then run `./mvnw test` to check the other 10 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 12 tests pass (10 station tests and 2 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## A WhatsApp channel

Add WHATSAPP: to the customer's phone, opt-in (`"whatsapp": true` in the preferences; absent means false). The notification service should not change.

**Done when:** the test in `WhatsAppChallengeTest` passes.

Hints

- One new `@Component` implementing `Channel`.
- Adding the enum value makes the compiler point at every `switch` that must decide about it.

#### `challenge/WhatsAppChallengeTest.java`

``` code
package com.tijori.notifications;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: a fourth channel, WHATSAPP, to the customer's phone number, off unless the customer turns it on
 * ("whatsapp": true in the preferences; absent means false). The notification service should not change at all.
 */
class WhatsAppChallengeTest extends ApiTest {

    @Test
    void whatsAppIsOneMoreChannelClass() throws Exception {
        notify(debit(1, 149900)).andExpect(jsonPath(statusOf("WHATSAPP")).value("SKIPPED"));
        preferences(1, "{\"sms\":true,\"email\":true,\"push\":true,\"whatsapp\":true}").andExpect(status().isOk());
        notify(debit(1, 149900)).andExpect(jsonPath(statusOf("WHATSAPP")).value("SENT"))
                .andExpect(jsonPath("$.deliveries[?(@.channel=='WHATSAPP')].text").value("Tijori: ₹1,499.00 debited from a/c XX4821 at BIGBASKET. Not you? Call 1800-000-0000."));
        notify("{\"customerId\":2,\"type\":\"NEW_DEVICE_LOGIN\"}").andExpect(jsonPath(statusOf("WHATSAPP")).value("SENT"));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## Retry what failed

Add `POST /notifications/{id}/retry`: deliver again only the channels that FAILED. A customer must never get a second SMS because email was down. Nothing failed: `409`; unknown id: `404`.

**Done when:** the test in `RetryChallengeTest` passes.

Hints

- Keep each notification's customer, notice and deliveries.
- Replace only FAILED deliveries; keep the others as they were.

#### `challenge/RetryChallengeTest.java`

``` code
package com.tijori.notifications;

import org.junit.jupiter.api.Test;
import org.springframework.test.context.bean.override.mockito.MockitoSpyBean;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doCallRealMethod;
import static org.mockito.Mockito.doThrow;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: POST /notifications/{id}/retry delivers again only what FAILED, and answers the notification. A
 * customer must not get a second SMS because email was down. Nothing failed: 409. Unknown id: 404.
 */
class RetryChallengeTest extends ApiTest {

    @MockitoSpyBean
    EmailChannel email;

    @Test
    void onlyTheFailedChannelIsTriedAgain() throws Exception {
        doThrow(new IllegalStateException("email provider timed out")).doCallRealMethod().when(email).deliver(any(), any());
        String body = notify(debit(1, 149900)).andExpect(jsonPath(statusOf("EMAIL")).value("FAILED")).andReturn().getResponse().getContentAsString();
        long id = Long.parseLong(body.replaceAll("^\\{\"id\":(\\d+).*", "$1"));
        mvc.perform(post("/notifications/{id}/retry", id)).andExpect(status().isOk())
                .andExpect(jsonPath(statusOf("EMAIL")).value("SENT")).andExpect(jsonPath(statusOf("SMS")).value("SENT"));
        assertThat(outbox.all()).extracting(Outbox.Sent::channel).containsExactlyInAnyOrder(
                Model.ChannelName.SMS, Model.ChannelName.PUSH, Model.ChannelName.EMAIL);   // one SMS, not two
        mvc.perform(post("/notifications/{id}/retry", id)).andExpect(status().isConflict());
        mvc.perform(post("/notifications/{id}/retry", 999_999)).andExpect(status().isNotFound());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## When is this overkill?

Tijori's HR tool sends one email when a payslip is ready, and nothing else. Would you write a `Channel` interface and an email class for it, or one method? List the signs that would make you split it later, and what splitting would cost then.

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test with the old class and its two March changes.
2.  List each reason to change: SMS limits, email layout, push wording, who-gets-what rules. One home each.
3.  Write the smallest interface the service needs from a channel, and one class per channel.
4.  Isolate failures, and test one channel failing alone.

## Design alternatives and trade-offs

| Approach                                            | What it costs                                                  | Verdict       |
|-----------------------------------------------------|----------------------------------------------------------------|---------------|
| One class per channel behind a two-method interface | A few small files.                                             | Chosen        |
| One service for all channels                        | Every change touches every channel.                            | The trap      |
| Abstract base class with template methods           | Shared code nobody can change alone; subclasses tied together. | Overkill here |
| A channel factory or registry                       | Spring already gives us every `Channel` bean as a list.        | Overkill here |
| A queue per channel                                 | Real isolation and retries; another system to run.             | At scale      |

## Database design

None in this station. A real service would keep a `notifications` table and a `deliveries` table (one row per channel and attempt), which is what challenge 2's retry needs to survive a restart.

# 3 · Go deeper: Production

Providers fail  
SMS gateways and email providers time out. Give each call a timeout, record the outcome per channel, and alert on a rising FAILED rate.

SMS rules in India  
Commercial SMS is sent through registered sender IDs and templates under TRAI's rules. Text changes may need a new template; keep SMS wording in one place.

Masking  
Responses and logs show masked addresses; full numbers stay with the provider call.

Preferences and law  
Which alerts a customer may turn off is a compliance decision. Here it is a demo rule; in a bank, the compliance team writes it down.

# 3 · Go deeper: Interview

## Interview takeaways

What does the single responsibility principle mean in practice?

A class should have one reason to change. SMS limits, email layout and the who-gets-what rule change for different reasons, at different times, by different people, so they live in different classes.

What is dependency inversion here?

NotificationService depends on the Channel interface; the SMS and email classes depend on it too. Neither side depends on the other's details, so either can change alone.

How does Spring help?

Injecting List\<Channel\> gives every Channel bean. Adding a channel is one new class; the service does not change.

Why catch exceptions per channel?

Channels are independent. Without it, the first failure stops every later channel: an email outage would stop debit alerts by SMS.

When is an interface overkill?

When there is one implementation, it is unlikely to grow, and tests do not need a substitute. Extract it when the second implementation or a real test need arrives.

## Self-check rubric

| Area        | Meets the bar                               | Above the bar                                      |
|-------------|---------------------------------------------|----------------------------------------------------|
| Correctness | All 10 tests pass.                          | You broke one channel and saw only its tests fail. |
| Design      | One class per channel, one small interface. | You can say what you did not add, and why.         |
| Resilience  | One failure does not stop the others.       | You know what a queue would add.                   |
| Details     | GSM-7 and Indian grouping right.            | You can explain UCS-2 and SMS parts.               |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any class that grows:

- How many different people or reasons would change this class?
- Can one part throw and stop parts that do not depend on it?
- Is an abstraction here because of a second implementation or a test, or "for later"?
- Would a new variant be a new class, or an edit to a long `if`?
