# Station 108 · Referral rewards without abuse

Working Systems · 0–2 years · Core · Quick commerce · Types: Database, Messaging, Idempotency

Spring Boot 4.1.1 · Java 25 · JdbcClient · transactional outbox with FOR UPDATE SKIP LOCKED · @Scheduled relay · RestClient · PostgreSQL 17 · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). Python 3 runs the simulated wallet in Try it yourself. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** The wallet is simulated: a reward is a credit request to a small server (no money moves). The order and sign-up services are simulated by the tests and by curl. Customers, phones and devices are made up.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 15 tests.

# 1 · Understand

## The problem in real life

1.  **₹100 for every friend**

    Basketo pays ₹100 when a customer's code brings in someone new.

2.  **Sixty friends, one phone**

    One person signed up sixty times on one phone with new SIM cards and his own code. The reward was paid at sign-up and only the phone number was checked: ₹6,000, and not one order.

3.  **The fix**

    A referral is only recorded at sign-up; the reward comes with the new customer's first delivered order. One referral per device, one reward per referral and per order, in the database. The wallet credit leaves through an outbox, retried and never paid twice.

Pay for the outcome you want, not for the step that is easy to fake, and make paying twice impossible.

## What are we building?

Referrals recorded at sign-up, rewarded once after a real delivered order, and credited to the referrer's wallet reliably.

## An everyday analogy

A gym gives a free month to members who bring a friend, once the friend has paid their first month, once per friend, and only one trial per household.

## How it works in 4 steps

1.  **Sign-up**: the code, the phone and the device are checked; a pending referral is recorded.
2.  **Delivered order**: the order service reports it, perhaps more than once.
3.  **Reward once**: the first delivered order of ₹500 or more creates the reward and a wallet message, together.
4.  **Send**: a background relay sends the credit, retries when the wallet is busy, and parks it when it cannot.

Check yourself: why not credit the wallet in the same request?

If the wallet is slow, the order service waits and retries; if the wallet succeeds and our commit then fails, money is credited with no record. The outbox makes the reward and the message one decision, and the sending a separate, repeatable step.

## What this station is not

- **No real wallet.** A simulated one; no money moves.
- **No sign-up or order system.** Their calls are simulated.
- **No fraud model.** Device and phone checks only; rings of real people are challenge 3.

## Key terms

| Term                     | Simple meaning                                                                                | Everyday example                                                             | In this project                       |
|--------------------------|-----------------------------------------------------------------------------------------------|------------------------------------------------------------------------------|---------------------------------------|
| **Referral**             | A customer invites someone new with their code; when it works out, they get a reward.         | "Bring a friend" at a gym.                                                   | `POST /referrals`                     |
| **Qualifying event**     | The moment that proves the referral was real: here, the new customer's first delivered order. | The friend actually paying for a month.                                      | a delivered order of ₹500 or more     |
| **Idempotent grant**     | The same event twice gives one reward, not two.                                               | A stamp card stamped once per visit, however often you show it.              | one reward per referral and per order |
| **Device check**         | One new account per phone handset, whatever SIM is in it.                                     | One free trial per household.                                                | `referrals_one_per_device`            |
| **Transactional outbox** | Write "send this" in the same transaction as the change, and send it afterwards.              | An outgoing-mail tray: the letter is in the tray before the clerk goes home. | `wallet_outbox`                       |
| **Dead letter**          | A message given up on, kept for a person instead of retried for ever.                         | The returned-mail shelf.                                                     | `DEAD`                                |

# 2 · Build: Spec

## Business problem

**Basketo** (a fictional grocery delivery app): referral rewards were farmed with new SIM cards. Rewards must follow real orders and be paid once.

## Acceptance criteria

Demo rules: ₹100 reward; first delivered order of at least ₹500; one referral per device; the wallet credit tried 5 times, 1, 2, 4 and 8 s apart.

1.  **Given** a valid code, a new phone and a new device, **then** `201`: a customer and a pending referral, nothing paid.
2.  **Given** an unknown code, a known phone, the code's own phone or device, or a device already used, **then** `404`, `409`, `422`, and no customer.
3.  **Given** a delivered order of ₹500 or more by a referred customer, **then** `201` and one reward; the same event again, or any later order, `200` with the same reward.
4.  **Given** an order that is not delivered, or is below ₹500, or a customer nobody referred, **then** no reward.
5.  **Given** a busy wallet, **then** the credit is retried with the same Idempotency-Key; a refused one, or one that never gets through, is `DEAD` for a person.

## Requirements

- One referral per referee and per device, one reward per referral and per order: named UNIQUE constraints.
- The reward and its wallet message in one transaction.
- No transaction open during a wallet call.

## Learning objectives

- Reward after a qualifying event, not before.
- Make a grant idempotent with keys and constraints.
- Build a transactional outbox with retries, backoff and a dead state.
- Test duplicate delivery, retries and dead letters against a real database.

# 2 · Build: API contract

## Endpoints

| Method | Path                           | Caller          | Purpose                                                                          |
|--------|--------------------------------|-----------------|----------------------------------------------------------------------------------|
| `POST` | `/referrals`                   | sign-up service | `{referralCode, name, phone, deviceId}`: a new customer with a pending referral. |
| `POST` | `/orders/{id}/referral-reward` | order service   | `{customerId, totalPaise, status}`: an order event, delivered at least once.     |
| `GET`  | `/rewards/{id}`                | support         | The reward and its wallet delivery: status, attempts, last error.                |

## Answers

| Status    | When                                                                                                     |
|-----------|----------------------------------------------------------------------------------------------------------|
| 201       | A customer signed up; a reward granted                                                                   |
| 200       | An order event with no new reward: `ALREADY_REWARDED` (the same reward), `NOT_REFERRED`, `BELOW_MINIMUM` |
| 400       | Bad phone, device id or body                                                                             |
| 404       | No such code or reward                                                                                   |
| 409       | The phone already has an account                                                                         |
| 422       | Own code or device; a device already used; an order that is not delivered                                |
| 401 / 403 | Not signed in / another service's door                                                                   |

## Captured examples

Captured with curl from the running app on 25 Oct 2026, in this order, against `docs/test-wallet.py`, a simulated wallet that credits once per Idempotency-Key. `Date`, connection and standard security headers are left out.

### Case 1: Neel signs up with Priya's code

**Why:** `201`, pending; the phone stored as +91 and ten digits.

Request

``` code
POST /referrals HTTP/1.1
Authorization: Basic c2lnbnVwOnNpZ251cC1kZW1vLXBhc3M=
Content-Type: application/json

{
  "referralCode": "RIYA100",
  "name": "Neel Joshi",
  "phone": "098765 43210",
  "deviceId": "device-neel-7f3a"
}
```

Response

``` code
HTTP/1.1 201 
Location: /customers/3
Content-Type: application/json

{
  "customerId": 3,
  "referralCode": "BK2HERR4",
  "referralId": 1,
  "status": "PENDING"
}
```

### Case 2: the same handset, a new SIM

**Why:** `422`: one referral per device.

Request

``` code
POST /referrals HTTP/1.1
Authorization: Basic c2lnbnVwOnNpZ251cC1kZW1vLXBhc3M=
Content-Type: application/json

{
  "referralCode": "RIYA100",
  "name": "Neel J",
  "phone": "9876500001",
  "deviceId": "device-neel-7f3a"
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "This device already has a Basketo account; referral codes are for new customers.",
  "instance": "/referrals",
  "status": 422,
  "title": "Unprocessable Content"
}
```

### Case 3: Priya's own number

**Why:** `422`: her own code.

Request

``` code
POST /referrals HTTP/1.1
Authorization: Basic c2lnbnVwOnNpZ251cC1kZW1vLXBhc3M=
Content-Type: application/json

{
  "referralCode": "RIYA100",
  "name": "Priya N",
  "phone": "+91 98123 45670",
  "deviceId": "device-priya-02"
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "This referral code belongs to you; codes are for inviting someone new.",
  "instance": "/referrals",
  "status": 422,
  "title": "Unprocessable Content"
}
```

### Case 4: Karan's number

**Why:** `409`: not a new customer.

Request

``` code
POST /referrals HTTP/1.1
Authorization: Basic c2lnbnVwOnNpZ251cC1kZW1vLXBhc3M=
Content-Type: application/json

{
  "referralCode": "RIYA100",
  "name": "Karan M",
  "phone": "9898989898",
  "deviceId": "device-karan-02"
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "This phone number already has a Basketo account.",
  "instance": "/referrals",
  "status": 409,
  "title": "Conflict"
}
```

### Case 5: a made-up code

**Why:** `404`.

Request

``` code
POST /referrals HTTP/1.1
Authorization: Basic c2lnbnVwOnNpZ251cC1kZW1vLXBhc3M=
Content-Type: application/json

{
  "referralCode": "FREE500",
  "name": "Someone",
  "phone": "9876500002",
  "deviceId": "device-some-0001"
}
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No customer has this referral code.",
  "instance": "/referrals",
  "status": 404,
  "title": "Not Found"
}
```

### Case 6: Neel places an order

**Why:** `422`: placing is not the qualifying event.

Request

``` code
POST /orders/40001/referral-reward HTTP/1.1
Authorization: Basic b3JkZXJzOm9yZGVycy1kZW1vLXBhc3M=
Content-Type: application/json

{
  "customerId": 3,
  "totalPaise": 65000,
  "status": "PLACED"
}
```

Response

``` code
HTTP/1.1 422 
Content-Length: 0
```

### Case 7: a ₹450 order is delivered

**Why:** below ₹500: no reward, the referral stays open.

Request

``` code
POST /orders/40002/referral-reward HTTP/1.1
Authorization: Basic b3JkZXJzOm9yZGVycy1kZW1vLXBhc3M=
Content-Type: application/json

{
  "customerId": 3,
  "totalPaise": 45000,
  "status": "DELIVERED"
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json

{
  "outcome": "BELOW_MINIMUM",
  "rewardId": null,
  "referrerId": null,
  "amountPaise": 0
}
```

### Case 8: a ₹650 order is delivered

**Why:** `201`, ₹100 to Priya. The wallet will be busy once.

Request

``` code
POST /orders/40003/referral-reward HTTP/1.1
Authorization: Basic b3JkZXJzOm9yZGVycy1kZW1vLXBhc3M=
Content-Type: application/json

{
  "customerId": 3,
  "totalPaise": 65000,
  "status": "DELIVERED"
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json

{
  "outcome": "REWARDED",
  "rewardId": 1,
  "referrerId": 1,
  "amountPaise": 10000
}
```

### Case 9: the order service sends the same event again

**Why:** `200`, the same reward.

Request

``` code
POST /orders/40003/referral-reward HTTP/1.1
Authorization: Basic b3JkZXJzOm9yZGVycy1kZW1vLXBhc3M=
Content-Type: application/json

{
  "customerId": 3,
  "totalPaise": 65000,
  "status": "DELIVERED"
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json

{
  "outcome": "ALREADY_REWARDED",
  "rewardId": 1,
  "referrerId": 1,
  "amountPaise": 10000
}
```

### Case 10: the reward, a moment later

**Why:** `SENT` after 2 attempts.

Request

``` code
GET /rewards/1 HTTP/1.1
Authorization: Basic c3VwcG9ydDpzdXBwb3J0LWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 122

{
  "id": 1,
  "referralId": 1,
  "orderId": 40003,
  "referrerId": 1,
  "amountPaise": 10000,
  "delivery": "SENT",
  "attempts": 2,
  "lastError": null
}
```

### Case 11: another reward, refused by the wallet

**Why:** `DEAD` after 1 attempt, with the reason, for a person.

Request

``` code
GET /rewards/2 HTTP/1.1
Authorization: Basic c3VwcG9ydDpzdXBwb3J0LWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 154

{
  "id": 2,
  "referralId": 2,
  "orderId": 40004,
  "referrerId": 2,
  "amountPaise": 10000,
  "delivery": "DEAD",
  "attempts": 1,
  "lastError": "the wallet refused the credit: 400"
}
```

## What the wallet received

``` code
Idempotency-Key: referral-reward-1  body: {"customerId":1,"amountPaise":10000,"reason":"referral reward"}  -> 503 
Idempotency-Key: referral-reward-1  body: {"customerId":1,"amountPaise":10000,"reason":"referral reward"}  -> 200 credited
Idempotency-Key: referral-reward-2  body: {"customerId":2,"amountPaise":10000,"reason":"referral reward"}  -> 400
```

A hand-written INSERT in `psql` that reuses Neel's device:

``` code
ERROR:  duplicate key value violates unique constraint "referrals_one_per_device"
DETAIL:  Key (device_id)=(device-neel-7f3a) already exists.
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                         | What happens                                               | Proved by                                                      |
|--------------------------------------------------------------|------------------------------------------------------------|----------------------------------------------------------------|
| The old way: 60 new SIMs                                     | ₹6,000 paid at sign-up                                     | `theOldWayPaysAtSignUpForEveryNewPhoneNumber`                  |
| The API: 60 sign-ups at once, one device                     | 1 referral, 59 `422`, nothing paid until a delivered order | `theApiTakesOneReferralPerDeviceAndPaysOnlyForADeliveredOrder` |
| A sign-up                                                    | `201`, pending, phone normalised                           | `aNewCustomerSignsUpWithACodeAndNothingIsPaidYet`              |
| Unknown code, known phone, own phone, used device, bad input | `404`, `409`, `422`, `422`, `400`; no customer             | `codesPhonesAndDevicesThatAreNotNewAreRefused`                 |
| Placed, below ₹500, not referred, delivered                  | `422`, no reward, no reward, `201`                         | `onlyADeliveredFirstOrderOfAtLeastFiveHundredRupeesIsRewarded` |
| Bad events, unknown reward, wrong service                    | `400`, `404`, `401`/`403`                                  | `badEventsAre400UnknownRewards404AndEachServiceHasItsOwnDoor`  |
| The same event twice                                         | One reward, one wallet message, credited once              | `theSameEventTwiceGivesOneReward`                              |
| A second delivered order                                     | The same reward                                            | `aSecondDeliveredOrderOfTheSameCustomerIsNotASecondReward`     |
| Twenty copies at once                                        | One `201`, nineteen `200`                                  | `twentyCopiesAtTheSameMomentGiveOneReward`                     |
| A busy wallet                                                | Retried with the same key; sent                            | `aBusyWalletIsTriedAgainWithTheSameKeyUntilItAnswers`          |
| A wallet that never answers well                             | `DEAD` after 3 tries; nothing more sent                    | `aWalletThatNeverAnswersWellParksTheCreditAsDead`              |
| A refused credit                                             | `DEAD` at once                                             | `aRefusedCreditIsDeadAtOnce`                                   |
| Applied but answered too late                                | Sent again with the same key; paid once                    | `aCreditAppliedButAnsweredTooLateIsSentAgainAndPaidOnce`       |
| Plain SQL against the rules                                  | Refused by named constraints                               | `theRulesAreNamedConstraintsInTheDatabase`                     |
| A referral that cannot be recorded                           | No customer left behind                                    | `aSignUpThatCannotRecordItsReferralLeavesNoCustomerBehind`     |

## The trap

Plausible but wrong

Rewarding at sign-up instead of after a real order, with no idempotency.

- **The old way** (on its own old tables): each sign-up with a code pays the referrer, and only the phone number must be new. Sixty SIM cards in one handset: sixty rewards, ₹6,000, no orders.
- **The API.** Sixty sign-ups at once from that handset: the first is accepted (nothing can tell it apart), the other fifty-nine are refused by the device rule, and nothing is paid until that one customer's ₹600 order is delivered.

While building, each part was undone once: no device check in Java turned 1 test red (the constraint still refused the concurrent ones, the Java check gives the clear message for an existing account); no device constraint 3; no own-code check 1; no row lock 1; no minimum 1; no outbox row 8; a new key per attempt 2; no retries 3; refused credits retried 1; phones not normalised 2; any order status rewarded 1. One check was taken out as redundant: looking the reward up by order before the referral (the referral's status already answers it).

``` code
package com.basketo.referrals;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static com.basketo.referrals.TestWallet.WALLET;
import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** One phone, sixty new SIM cards: Karan refers "new customers" with his own code, sixty times. Written first. */
class ReferralAbuseTrapTest extends ApiTest {

    /**
     * The old way, on the old tables: a reward the moment someone signs up with a code, checked only against the phone
     * number. Each new SIM card is a new phone number.
     */
    @Test
    void theOldWayPaysAtSignUpForEveryNewPhoneNumber() {
        jdbc.sql("CREATE TEMP TABLE old_customers (phone TEXT PRIMARY KEY, device_id TEXT)").update();
        jdbc.sql("CREATE TEMP TABLE old_rewards (referrer TEXT, amount_paise BIGINT)").update();
        try {
            for (int i = 0; i < 60; i++) {
                String phone = "+9170000000" + String.format("%02d", i);
                if (jdbc.sql("SELECT count(*) FROM old_customers WHERE phone = ?").param(phone).query(Integer.class).single() == 0) {
                    jdbc.sql("INSERT INTO old_customers VALUES (?, 'device-of-one-person')").param(phone).update();
                    jdbc.sql("INSERT INTO old_rewards VALUES ('KARAN50', 10000)").update();
                }
            }
            long paid = jdbc.sql("SELECT sum(amount_paise) FROM old_rewards").query(Long.class).single();
            assertThat(paid).as("₹6,000 in rewards, and not one order").isEqualTo(600_000);
        } finally {
            jdbc.sql("DROP TABLE old_customers, old_rewards").update();
        }
    }

    @Test
    void theApiTakesOneReferralPerDeviceAndPaysOnlyForADeliveredOrder() throws Exception {
        List<Integer> statuses = atOnce(60, i -> signUp("KARAN50", "+9170000000" + String.format("%02d", i), "device-of-one-person")
                .andReturn().getResponse().getStatus());
        assertThat(statuses).filteredOn(s -> s == 201).hasSize(1);
        assertThat(statuses).filteredOn(s -> s == 422).hasSize(59);
        assertThat(count("referrals")).isEqualTo(1);
        assertThat(count("rewards")).as("nothing paid at sign-up").isZero();

        long customer = jdbc.sql("SELECT referee_id FROM referrals").query(Long.class).single();
        order(9001, customer, 60_000, "DELIVERED").andExpect(status().isCreated());   // a real first order of ₹600
        long reward = jdbc.sql("SELECT id FROM rewards").query(Long.class).single();
        awaitDelivery(reward, "SENT");
        assertThat(WALLET.creditedTo(KARAN)).isEqualTo(10_000);
    }

    interface Work<T> {
        T call(int i) throws Exception;
    }

    /** n virtual threads, released together. */
    static <T> List<T> atOnce(int n, Work<T> work) throws Exception {
        CountDownLatch start = new CountDownLatch(1);
        List<Future<T>> futures = new ArrayList<>();
        try (var pool = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < n; i++) {
                int index = i;
                futures.add(pool.submit(() -> {
                    start.await();
                    return work.call(index);
                }));
            }
            start.countDown();
            List<T> out = new ArrayList<>();
            for (Future<T> f : futures) {
                out.add(f.get());
            }
            return out;
        }
    }
}
```

# 2 · Build: Set up & code

## Set up and run

| You need | Version                                                           | Check with          |
|----------|-------------------------------------------------------------------|---------------------|
| JDK      | 25 (recommended). JDK 21 also works, see below                    | `java -version`     |
| Docker   | Docker Desktop (Windows, macOS) or Docker Engine (Linux), running | `docker info`       |
| Python 3 | Only for the simulated wallet                                     | `python3 --version` |
| Maven    | Not needed: the project ships the Maven wrapper                   |                     |

**macOS / Linux**

``` code
docker compose up -d --wait          # PostgreSQL 17 on localhost:5432
python3 docs/test-wallet.py 9095 &   # the simulated wallet
./mvnw spring-boot:run               # the API on http://localhost:8080
./mvnw test                          # all 15 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d --wait
Start-Process python -ArgumentList 'docs/test-wallet.py','9095'
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Stop the simulated wallet, deliver an order, and watch the credit wait and retry; start the wallet again and it goes through:

``` code
curl -u orders:orders-demo-pass -H 'Content-Type: application/json' \
  -d '{"customerId":3,"totalPaise":65000,"status":"DELIVERED"}' localhost:8080/orders/40010/referral-reward
curl -u support:support-demo-pass localhost:8080/rewards/1   # attempts and last_error grow until the wallet is back
```

## Troubleshooting

| You see                          | Cause                                                               | Fix                                                               |
|----------------------------------|---------------------------------------------------------------------|-------------------------------------------------------------------|
| A reward stays `PENDING`         | The wallet is down or slow; the relay is waiting between tries.     | Check `last_error`; it goes out once the wallet answers.          |
| A reward is `DEAD`               | The wallet refused it, or it never got through in 5 tries.          | Fix the cause; resending is challenge 2.                          |
| `422` for a genuine new customer | Their handset was used for a referral before (a second-hand phone). | Expected with this rule; support can sign them up without a code. |

## Project layout

``` tree
stations/108-referral-rewards-without-abuse/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/basketo/referrals/
│   ├── ReferralController.java   ├── Referrals.java   ├── WalletRelay.java   ├── Phones.java
│   └── SecurityConfig.java, ProblemResponses.java, ReferralsApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__referrals_and_rewards.sql, V2__demo_customers.sql
├── src/test/java/com/basketo/referrals/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, simulated wallet, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the relay and the database.

#### `src/main/java/com/basketo/referrals/ReferralController.java`

Does  
The endpoints.

Why  
Validates input, normalises the phone, and turns only DELIVERED into a reward attempt.

Without it  
A reward for a placed, cancelled or returned order.

#### `src/main/java/com/basketo/referrals/Referrals.java`

Does  
The rules.

Why  
Sign-up checks and a pending referral; on a delivered order, the referral locked, then one reward and one wallet message together.

Without it  
Rewards at sign-up; two rewards for one event.

- The device check in Java gives a clear message; the UNIQUE constraint is what holds when sixty sign-ups arrive at once: the trap test sends them together.

#### `src/main/java/com/basketo/referrals/WalletRelay.java`

Does  
The outbox relay.

Why  
Claims due messages for a minute, sends with an Idempotency-Key, retries with doubling waits, parks as DEAD.

Without it  
A lost credit; a credit paid twice; a transaction held while the wallet thinks.

- The key only helps if the wallet honours it: agree it with the wallet team. The simulated one does.
- Shortcut: the relay polls every second; at scale, a notification (LISTEN/NOTIFY or a message broker) wakes it instead.

#### `src/main/java/com/basketo/referrals/Phones.java`

Indian mobile numbers in one form, so formatting cannot make an old number look new.

#### `src/main/java/com/basketo/referrals/SecurityConfig.java`

One sign-in per calling service; each has its own door.

#### `src/main/resources/db/migration/V1__referrals_and_rewards.sql`

Does  
The tables.

Why  
Named UNIQUE and CHECK constraints for every rule above, and the outbox.

Without it  
Any writer breaking the rules.

#### `src/main/resources/db/migration/V2__demo_customers.sql`

Priya and Karan.

#### `src/main/resources/application.yaml`

Reward, minimum, wallet address, retries.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                           | Test class                     | Result |
|---------------|-------------------------------------------------------|--------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found              | `ReferralContractTest` (4)     | pass   |
| Every station | Reproduce the failure before the fix                  | `ReferralAbuseTrapTest` (2)    | pass   |
| Database      | Rollback and constraint tests against a real database | `ReferralDatabaseTest` (2)     | pass   |
| Messaging     | Duplicate delivery, retry and dead letter             | `WalletMessagingTest` (4)      | pass   |
| Idempotency   | The same request twice gives one effect               | `ReferralRewardReplayTest` (3) | pass   |

PostgreSQL 17 in Docker; a simulated wallet that credits once per key and answers as each test plans; the relay polls every 100 ms and retries 50 ms then 100 ms apart, so a dead letter is reached in under a second.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.basketo.referrals.ReferralContractTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.basketo.referrals.ReferralAbuseTrapTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.basketo.referrals.ReferralRewardReplayTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.basketo.referrals.WalletMessagingTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.basketo.referrals.ReferralDatabaseTest
[INFO] Tests run: 15, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/basketo/referrals/ReferralAbuseTrapTest.java`

Written first: sixty SIMs, the old way and the API.

#### `src/test/java/com/basketo/referrals/ReferralContractTest.java`

Sign-ups, order events, answers, doors.

#### `src/test/java/com/basketo/referrals/ReferralRewardReplayTest.java`

The same event again; twenty at once.

#### `src/test/java/com/basketo/referrals/WalletMessagingTest.java`

Retries, dead letters, a late answer.

#### `src/test/java/com/basketo/referrals/ReferralDatabaseTest.java`

Named constraints with plain SQL; a rollback.

#### `src/test/java/com/basketo/referrals/TestWallet.java`

The simulated wallet.

#### `src/test/java/com/basketo/referrals/ApiTest.java`

Shared setup.

#### `src/test/java/com/basketo/referrals/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/basketo/referrals/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=MonthlyLimitChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 15 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 19 tests pass (15 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## A monthly limit

At most `basketo.referrals.max-rewards-per-month` rewards per referrer per calendar month, India time (2 in the test). Past it, the outcome is `MONTHLY_LIMIT`, nothing is paid, and the referral stays open for next month.

**Done when:** both tests in `MonthlyLimitChallengeTest` pass.

Hints

- Count the referrer's rewards since the start of this month in Asia/Kolkata.
- The referral row is already locked; lock the referrer's row too if two of their referrals can finish at once.

#### `challenge/MonthlyLimitChallengeTest.java`

``` code
package com.basketo.referrals;

import org.junit.jupiter.api.Test;
import org.springframework.test.context.TestPropertySource;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: at most N rewards a calendar month (India time) per referrer; 2 here. */
@TestPropertySource(properties = "basketo.referrals.max-rewards-per-month=2")
class MonthlyLimitChallengeTest extends ApiTest {

    @Test
    void theThirdRewardThisMonthWaitsAndTheReferralStaysOpen() throws Exception {
        long a = referredCustomer("9876500101", "device-new-0101");
        long b = referredCustomer("9876500102", "device-new-0102");
        long c = referredCustomer("9876500103", "device-new-0103");
        order(8101, a, 60_000, "DELIVERED").andExpect(status().isCreated());
        order(8102, b, 60_000, "DELIVERED").andExpect(status().isCreated());
        order(8103, c, 60_000, "DELIVERED").andExpect(status().isOk()).andExpect(jsonPath("$.outcome").value("MONTHLY_LIMIT"));
        assertThat(count("rewards")).isEqualTo(2);
        assertThat(jdbc.sql("SELECT status FROM referrals WHERE referee_id = ?").param(c).query(String.class).single()).isEqualTo("PENDING");
    }

    @Test
    void anotherReferrersRewardsDoNotCount() throws Exception {
        long a = referredCustomer("9876500104", "device-new-0104");
        long b = referredCustomer("9876500105", "device-new-0105");
        long k = json(signUp("KARAN50", "9876500106", "device-new-0106")).path("customerId").asLong();
        order(8104, a, 60_000, "DELIVERED").andExpect(status().isCreated());
        order(8105, b, 60_000, "DELIVERED").andExpect(status().isCreated());
        order(8106, k, 60_000, "DELIVERED").andExpect(status().isCreated());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## Send a dead credit again

Support fixes the cause of a `DEAD` credit and asks for it to be sent again: `POST /rewards/{id}/delivery-retry` (support only) answers `202` and puts it back in the outbox with fresh attempts and the same key; a credit that is not dead is `409`; an unknown one `404`.

**Done when:** both tests in `RetryDeadCreditChallengeTest` pass.

Hints

- One conditional UPDATE: `... WHERE reward_id = ? AND status = 'DEAD'`.
- Keep the Idempotency-Key: the wallet may have applied it after all.

#### `challenge/RetryDeadCreditChallengeTest.java`

``` code
package com.basketo.referrals;

import org.junit.jupiter.api.Test;

import static com.basketo.referrals.TestWallet.WALLET;
import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 2: support fixes the cause of a DEAD credit, then sends it again with the same key. */
class RetryDeadCreditChallengeTest extends ApiTest {

    @Test
    void aDeadCreditIsSentAgainOnRequestAndPaidOnce() throws Exception {
        WALLET.planned.add(400);
        long customer = referredCustomer("9876500110", "device-new-0110");
        long reward = json(order(8201, customer, 60_000, "DELIVERED")).path("rewardId").asLong();
        awaitDelivery(reward, "DEAD");

        mvc.perform(post("/rewards/{id}/delivery-retry", reward).with(httpBasic("support", "support-demo-pass"))).andExpect(status().isAccepted());
        awaitDelivery(reward, "SENT");
        assertThat(WALLET.requests).hasSize(2).allMatch(r -> r.key().equals("referral-reward-" + reward));
        assertThat(WALLET.creditedTo(PRIYA)).isEqualTo(10_000);
    }

    @Test
    void onlyADeadCreditCanBeRetriedAndOnlyBySupport() throws Exception {
        long customer = referredCustomer("9876500111", "device-new-0111");
        long reward = json(order(8202, customer, 60_000, "DELIVERED")).path("rewardId").asLong();
        awaitDelivery(reward, "SENT");
        mvc.perform(post("/rewards/{id}/delivery-retry", reward).with(httpBasic("support", "support-demo-pass"))).andExpect(status().isConflict());
        mvc.perform(post("/rewards/{id}/delivery-retry", 999).with(httpBasic("support", "support-demo-pass"))).andExpect(status().isNotFound());
        mvc.perform(post("/rewards/{id}/delivery-retry", reward).with(httpBasic("orders", "orders-demo-pass"))).andExpect(status().isForbidden());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## A ring of real people

Ten friends each sign up on their own phones with each other's codes, place one ₹500 order, return it after the reward, and move on. Every rule here passes. Which signals would you add (returns, payment cards, delivery addresses), when would a reward wait for a return window, and who reviews the rest without punishing honest referrers?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: sixty sign-ups from one device.
2.  Move the reward to the delivered order; record only a referral at sign-up.
3.  Constraints for each "once"; a row lock for the decision.
4.  An outbox and a relay for the wallet; retries, backoff, dead.

## Design alternatives and trade-offs

| Approach                                | What it costs                                                                          | Verdict  |
|-----------------------------------------|----------------------------------------------------------------------------------------|----------|
| Outbox table + relay                    | A table and a background job.                                                          | Chosen   |
| Call the wallet inside the transaction  | A slow wallet holds the transaction; a commit failure after a credit loses the record. | Avoid    |
| Call the wallet after commit, no outbox | A crash between commit and call loses the credit.                                      | Avoid    |
| A message broker                        | Another system to run; still needs an outbox to publish reliably.                      | At scale |
| Reward at sign-up                       | Pays for the step that is easy to fake.                                                | The trap |

## Database design

| Constraint                                              | Rule                            | Why                                             |
|---------------------------------------------------------|---------------------------------|-------------------------------------------------|
| `referrals_one_per_referee`, `referrals_one_per_device` | UNIQUE                          | One referral per new customer, and per handset. |
| `referrals_not_self`                                    | referrer ≠ referee              | No referring yourself, even by SQL.             |
| `rewards_one_per_referral`, `rewards_one_per_order`     | UNIQUE                          | One reward, whatever arrives twice.             |
| `customers_phone_unique`                                | UNIQUE on the normalised number | One account per number.                         |
| `wallet_outbox_one_per_reward`, `wallet_outbox_status`  | UNIQUE; known states            | One credit per reward.                          |

**Transaction boundaries:** a sign-up creates the customer and the referral together; a delivered order locks the referral and writes the reward, the referral's new status and the outbox row together; the relay claims rows in one short transaction, calls the wallet with none open, and records the result in another.

``` code
-- Customers, referrals, rewards, and the outbox of wallet credits. Money in paise.
CREATE TABLE customers (
    id            BIGSERIAL PRIMARY KEY,
    name          TEXT NOT NULL,
    phone         TEXT NOT NULL CONSTRAINT customers_phone_unique UNIQUE,   -- normalised: +91 and 10 digits
    device_id     TEXT NOT NULL,
    referral_code TEXT NOT NULL CONSTRAINT customers_code_unique UNIQUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX customers_by_device ON customers (device_id);

CREATE TABLE referrals (
    id          BIGSERIAL PRIMARY KEY,
    referrer_id BIGINT NOT NULL REFERENCES customers (id),
    -- A new customer is referred once, by one person.
    referee_id  BIGINT NOT NULL REFERENCES customers (id) CONSTRAINT referrals_one_per_referee UNIQUE,
    -- The device the new customer signed up on: one referral per device, ever. This is what stops one person
    -- referring himself with sixty new phone numbers.
    device_id   TEXT   NOT NULL CONSTRAINT referrals_one_per_device UNIQUE,
    status      TEXT   NOT NULL CONSTRAINT referrals_status CHECK (status IN ('PENDING', 'REWARDED')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT referrals_not_self CHECK (referrer_id <> referee_id)
);

CREATE TABLE rewards (
    id           BIGSERIAL PRIMARY KEY,
    -- One reward per referral, and one per qualifying order: a second delivery of the same event finds it taken.
    referral_id  BIGINT NOT NULL REFERENCES referrals (id) CONSTRAINT rewards_one_per_referral UNIQUE,
    order_id     BIGINT NOT NULL CONSTRAINT rewards_one_per_order UNIQUE,
    referrer_id  BIGINT NOT NULL REFERENCES customers (id),
    amount_paise BIGINT NOT NULL CONSTRAINT rewards_amount_positive CHECK (amount_paise > 0),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Wallet credits waiting to be sent, written in the same transaction as the reward (a transactional outbox).
CREATE TABLE wallet_outbox (
    id              BIGSERIAL PRIMARY KEY,
    reward_id       BIGINT NOT NULL REFERENCES rewards (id) CONSTRAINT wallet_outbox_one_per_reward UNIQUE,
    status          TEXT   NOT NULL DEFAULT 'PENDING' CONSTRAINT wallet_outbox_status CHECK (status IN ('PENDING', 'SENT', 'DEAD')),
    attempts        INT    NOT NULL DEFAULT 0 CONSTRAINT wallet_outbox_attempts CHECK (attempts >= 0),
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    claimed_until   TIMESTAMPTZ,
    last_error      TEXT,
    sent_at         TIMESTAMPTZ
);
CREATE INDEX wallet_outbox_due ON wallet_outbox (next_attempt_at) WHERE status = 'PENDING';
```

# 3 · Go deeper: Production

## Real-world considerations

Watching the outbox  
Alert on any `DEAD` row, and on the oldest `PENDING` row passing a few minutes: both mean customers waiting for money they were promised.

Device ids  
An app-generated id survives SIM changes but not a reinstall on some phones; combine it with other signals rather than trusting it alone.

Returns  
A reward for an order later returned is the next loophole: hold rewards until the return window closes (challenge 3).

Cleaning up  
Sent outbox rows can be deleted after a few weeks; keep rewards for accounting.

# 3 · Go deeper: Interview

## Interview takeaways

When should a referral reward be paid?

After the event that shows the referral was real (a delivered first order), not at sign-up.

How do you make a reward grant idempotent?

Key it on what must be unique (one per referral, one per order) with database constraints, and lock the row while deciding.

What is a transactional outbox?

Writing the message to send in the same transaction as the change, then sending it from that table, so neither is lost without the other.

How do retries avoid paying twice?

The same idempotency key on every attempt, and a receiver that honours it.

What is a dead letter?

A message that will not succeed by retrying (refused, or out of attempts), parked with its reason for a person.

Why not hold a transaction while calling the wallet?

It holds a database connection and locks for as long as the wallet takes.

## Self-check rubric

| Area        | Meets the bar          | Above the bar                                                                              |
|-------------|------------------------|--------------------------------------------------------------------------------------------|
| Correctness | All 15 tests pass.     | You ran the flawed version and explained each failure.                                     |
| Abuse       | Reward after an order. | Every "once" is a constraint, and you can name what still gets through.                    |
| Delivery    | The credit is sent.    | Outbox, retries with backoff, dead letters, idempotency keys, no transaction during calls. |
| Tests       | Happy path.            | Duplicates, concurrency, retries, dead letters and late answers, against a real database.  |

# 3 · Go deeper: Review

## The pull request

A teammate "simplifies" the reward: "the constraint is enough without a lock, and the outbox is a lot of machinery for one HTTP call". Read the file and list every problem before opening the findings.

#### `review/Referrals.java`

``` code
package com.basketo.referrals;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;
import org.springframework.transaction.annotation.Transactional;

import java.security.SecureRandom;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;

/**
 * Referrals are recorded at sign-up and rewarded only when the new customer's first qualifying order is delivered.
 * Each rule that matters is also a constraint: one referral per new customer and per device, one reward per referral
 * and per order.
 */
@Service
class Referrals {

    enum Outcome { REWARDED, ALREADY_REWARDED, NOT_REFERRED, BELOW_MINIMUM }

    record SignUp(long customerId, String referralCode, long referralId, String status) {
    }

    record Result(Outcome outcome, Long rewardId, Long referrerId, long amountPaise) {
    }

    record Reward(long id, long referralId, long orderId, long referrerId, long amountPaise, String delivery, int attempts, String lastError) {
    }

    static final class NoSuchCode extends RuntimeException {
    }

    static final class PhoneTaken extends RuntimeException {
    }

    /** The code belongs to this phone, or this device already has an account or a referral. */
    static final class NotANewCustomer extends RuntimeException {
        NotANewCustomer(String message) {
            super(message);
        }
    }

    private static final String CODE_LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
    private static final SecureRandom RANDOM = new SecureRandom();
    private final JdbcClient jdbc;
    private final long rewardPaise;
    private final long minimumOrderPaise;
    private final RestClient wallet;

    Referrals(JdbcClient jdbc, @Value("${basketo.referrals.reward-paise}") long rewardPaise,
              @Value("${basketo.referrals.minimum-order-paise}") long minimumOrderPaise, @Value("${basketo.wallet.url}") String walletUrl) {
        this.jdbc = jdbc;
        this.wallet = RestClient.create(walletUrl);
        this.rewardPaise = rewardPaise;
        this.minimumOrderPaise = minimumOrderPaise;
    }

    /** A new customer signs up with someone's code: the customer and a PENDING referral. No reward yet. */
    @Transactional
    SignUp signUp(String code, String name, String phone, String deviceId) {
        record Referrer(long id, String phone, String deviceId) {
        }
        Referrer referrer = jdbc.sql("SELECT id, phone, device_id FROM customers WHERE referral_code = ?").param(code.strip().toUpperCase(Locale.ROOT))
                .query(Referrer.class).optional().orElseThrow(NoSuchCode::new);
        if (referrer.phone().equals(phone) || referrer.deviceId().equals(deviceId)) {
            throw new NotANewCustomer("This referral code belongs to you; codes are for inviting someone new.");
        }
        if (jdbc.sql("SELECT count(*) FROM customers WHERE device_id = ?").param(deviceId).query(Integer.class).single() > 0) {
            throw new NotANewCustomer("This device already has a Basketo account; referral codes are for new customers.");
        }
        long customer;
        try {
            customer = jdbc.sql("INSERT INTO customers (name, phone, device_id, referral_code) VALUES (?, ?, ?, ?) RETURNING id")
                    .params(name, phone, deviceId, newCode()).query(Long.class).single();
        } catch (DuplicateKeyException e) {
            throw new PhoneTaken();
        }
        long referral;
        try {
            referral = jdbc.sql("INSERT INTO referrals (referrer_id, referee_id, device_id, status) VALUES (?, ?, ?, 'PENDING') RETURNING id")
                    .params(referrer.id(), customer, deviceId).query(Long.class).single();
        } catch (DuplicateKeyException e) {
            // Two sign-ups on one device at the same moment: the check above passed for both; the constraint did not.
            throw new NotANewCustomer("This device already has a Basketo account; referral codes are for new customers.");
        }
        String newCode = jdbc.sql("SELECT referral_code FROM customers WHERE id = ?").param(customer).query(String.class).single();
        return new SignUp(customer, newCode, referral, "PENDING");
    }

    /**
     * The order service reports a delivered order. Delivered at least once: the same event may come twice, and the
     * answer is the same reward. The unique constraints stop a second reward, so no lock is needed.
     */
    @Transactional
    Result orderDelivered(long orderId, long customerId, long totalPaise) {
        record Referral(long id, long referrerId, String status) {
        }
        Optional<Referral> referral = jdbc.sql("SELECT id, referrer_id, status FROM referrals WHERE referee_id = ?").param(customerId)
                .query(Referral.class).optional();
        if (referral.isEmpty()) {
            return new Result(Outcome.NOT_REFERRED, null, null, 0);
        }
        if (referral.get().status().equals("REWARDED")) {
            return jdbc.sql("SELECT id, referrer_id, amount_paise FROM rewards WHERE referral_id = ?").param(referral.get().id())
                    .query((rs, n) -> new Result(Outcome.ALREADY_REWARDED, rs.getLong(1), rs.getLong(2), rs.getLong(3))).single();
        }
        if (totalPaise < minimumOrderPaise) {
            return new Result(Outcome.BELOW_MINIMUM, null, null, 0);
        }
        long reward = jdbc.sql("INSERT INTO rewards (referral_id, order_id, referrer_id, amount_paise) VALUES (?, ?, ?, ?) RETURNING id")
                .params(referral.get().id(), orderId, referral.get().referrerId(), rewardPaise).query(Long.class).single();
        jdbc.sql("UPDATE referrals SET status = 'REWARDED' WHERE id = ?").param(referral.get().id()).update();
        // Credit the wallet right away: no outbox table and no scheduler to run.
        wallet.post().uri("/credits").header("Idempotency-Key", "referral-reward-" + reward)
                .body(Map.of("customerId", referral.get().referrerId(), "amountPaise", rewardPaise, "reason", "referral reward"))
                .retrieve().toBodilessEntity();
        return new Result(Outcome.REWARDED, reward, referral.get().referrerId(), rewardPaise);
    }

    Optional<Reward> reward(long id) {
        return jdbc.sql("""
                        SELECT r.id, r.referral_id, r.order_id, r.referrer_id, r.amount_paise, o.status AS delivery, o.attempts, o.last_error
                        FROM rewards r JOIN wallet_outbox o ON o.reward_id = r.id WHERE r.id = ?""").param(id).query(Reward.class).optional();
    }

    private static String newCode() {
        StringBuilder s = new StringBuilder("BK");
        for (int i = 0; i < 6; i++) {
            s.append(CODE_LETTERS.charAt(RANDOM.nextInt(CODE_LETTERS.length())));
        }
        return s.toString();
    }
}
```

## Findings

1No lock on the referral

"The unique constraint already stops a second reward": it stops the second row, as an error. Two deliveries of the same event at once both read the referral as pending; one wins, the other gets a 500, and the order service retries something that had already succeeded.

**Test evidence:** `twentyCopiesAtTheSameMomentGiveOneReward` fails: 500s for copies that should be 200s.

2The wallet called inside the transaction

"Why a table and a scheduler? Call the wallet when the reward is made": while the wallet thinks, the transaction and its locks are held; when it is down, the reward is rolled back and the order service is told to retry; and when the wallet succeeds but the commit fails, the money is credited with no reward on record.

**Test evidence:** All four `WalletMessagingTest` tests fail, and `theSameEventTwiceGivesOneReward`, `onlyADeliveredFirstOrderOfAtLeastFiveHundredRupeesIsRewarded` and `theApiTakesOneReferralPerDeviceAndPaysOnlyForADeliveredOrder` with them: a busy wallet fails the reward itself, and there is no delivery record to look at.

## Same tests, flawed version

From `docs/review-run.txt`: the flawed file copied over the real one, then the full suite run.

| Test class                 | Fixed version | Flawed version |
|----------------------------|---------------|----------------|
| `ReferralDatabaseTest`     | 2 / 2         | 2 / 2          |
| `ReferralAbuseTrapTest`    | 2 / 2         | 1 / 2          |
| `ReferralContractTest`     | 4 / 4         | 3 / 4          |
| `ReferralRewardReplayTest` | 3 / 3         | 1 / 3          |
| `WalletMessagingTest`      | 4 / 4         | 0 / 4          |

With a healthy wallet and one event at a time, the flawed version pays the right people the right amount.
