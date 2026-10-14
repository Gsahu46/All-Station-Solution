# Station 018 plan: Payment methods with sealed interfaces

**Problem.** Paysetu models UPI, card, net banking and wallet as one class with a nullable field per method. The
refund path checks fields in an if-chain and forgot wallets (returns null); a body with UPI and card fields is accepted.

**Endpoint.** `POST /payment-intents` (orderId, amountPaise Rs 1..Rs 1 lakh, method with "type") 201 with the method,
next action and refund route; 400 unknown or missing type, mixed fields, bad field; 422 a bank that is not offered.
Nothing stored (challenge 1 stores it).

**Data.** `sealed interface PaymentMethod` with records Upi, Card (network, last4, write-only token: never a card
number), NetBanking (bank code, upper-case), Wallet (mobile, shown masked). Jackson picks the record by "type";
fail-on-unknown-properties refuses mixed fields. `Methods.nextAction` / `refundRoute`: switches with record patterns,
no default.

**Trap.** `ForgottenWalletTrapTest`: old route null for a wallet; old class picks UPI from a UPI+card body; new model
refunds wallets and gives 400 for the mixed body. Compile error captured with a case removed. Mutations: lenient
JSON -> 1 red; token echoed -> 1 red; WALLET unregistered -> 3 red.

**Tests.** Trap, `PaymentIntentContractTest`, `EveryMethodTest` (permitted subclasses by reflection: registered for JSON,
next action and refund route for each).

**Practice.** 1: store + GET /payment-intents/{id} + Location. 2: PAY_LATER as a fifth record.
Design: where the next action should live when methods multiply.
