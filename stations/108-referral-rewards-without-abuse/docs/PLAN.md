# Station 108 plan: Referral rewards without abuse

**Problem.** Basketo (fictional grocery delivery): one person "referred" himself 60 times with new SIM cards on one
phone and collected ₹6,000. Rewards were paid at sign-up, checked only against the phone number, with no idempotency.

**Endpoints.** `POST /referrals {referralCode, name, phone, deviceId}` (the sign-up service): 201 a customer and a
PENDING referral, nothing paid; 404 unknown code; 409 phone already a customer (numbers normalised to +91 and 10 digits);
422 own code or a device that already has an account or a referral; 400 bad input. `POST /orders/{id}/referral-reward
{customerId, totalPaise, status}` (the order service, at least once): 422 unless DELIVERED; 201 REWARDED (₹100, first
delivered order of at least ₹500); 200 ALREADY_REWARDED (same reward), NOT_REFERRED, BELOW_MINIMUM. `GET /rewards/{id}`
(support): the reward and its wallet delivery.

**Fix.** Reward only after a delivered order; one referral per new customer and per device (named UNIQUE constraints);
one reward per referral and per order; the referral row locked while deciding. The wallet credit is written to an
outbox in the same transaction and sent by WalletRelay: rows claimed for a minute (FOR UPDATE SKIP LOCKED, no
transaction during the call), Idempotency-Key referral-reward-{id}, retries 1 s, 2 s, 4 s, 8 s, DEAD after 5 tries or at
once on a 4xx (not 408/429). Simulation: a credit is a request to a simulated wallet; no money moves.

**Trap.** `ReferralAbuseTrapTest`: the old way (temp tables, reward per new phone at sign-up) pays ₹6,000 for 60 SIMs;
the API, 60 sign-ups at once from one device: 1 referral, 59 x 422, nothing paid until a delivered order.

**Review.** No row lock ("the unique constraint stops a second reward") and the wallet called inside the transaction instead of the outbox.

**Practice.** 1: a monthly reward limit per referrer. 2: support retries a DEAD credit. 3 (paper): rings of real people.
