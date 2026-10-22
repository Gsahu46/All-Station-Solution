# Station 087 plan: Saving cards with network tokens

**Problem.** A merchant on Paysetu (fictional) kept card numbers for one-click checkout, "just for retries". A breach
exposed them. RBI's card-on-file tokenisation rules (in force since 1 October 2022) allow only card issuers and card
networks to store card data.

**Endpoints.** `POST /customers/{id}/saved-cards` {cardNumber, expiryMonth, expiryYear, consent}: check digit and
length (400), consent must be true (400), network refuses expired or unsupported cards (422); 201 with id, network,
last 4, expiry; never the number or token. `GET /customers/{id}/saved-cards`: own active cards. `POST /payments`
{orderId, savedCardId, amountPaise}: token + one-time cryptogram from the network; 201, 402 declined, 404 not your
card, 422 expired (IST month); same order again: same payment, even after the card expired; another customer's order
id 409. Sign-in: HTTP Basic, asha and rohan; another customer's path 403; no sign-in 401.

**Simulation.** `SimNetwork` stands for the network's token service: its vault (a map) holds the number, outside
Paysetu's code and tables. Nothing is charged.

**Database.** saved_cards: token shape `tkn_` + 20 letters, last4 shape (so no column can hold a card number),
network, expiry, status, consent time. payments: order once, pending first (written before the network is called).

**Trap.** `CardNumberStorageTrapTest`: a search over every text column finds the number in an old-design table; after
saving, paying, a decline, a retry and two bad requests it finds nothing in our tables or the log; the request's
toString masks the number.

**Found while building.** (1) A record's default toString prints every field: masked. (2) A token the network made but
our insert failed to record was left usable: deleted at the network on failure. (3) The early replay check looked
redundant (the unique order id returns the same payment), but without it a retry after the card expired was refused:
test added.

**Mutations.** no check digit -> 2; no length check -> 1 (after fixing the test number); number in the error -> 1;
number stored as token -> 8; no owner check on paths -> 1; any customer's card -> 1; order id owner -> 1; no expiry
-> 1; expiry month in UTC -> 1; no network delete on failure -> 1; no consent -> 1; default toString -> 1; no early
replay -> 1.

**Review.** A debug log of the request (default toString) and no owner check on listing.

**Practice.** 1: delete a saved card (and its token). 2: network token events (re-issued card keeps its token,
suspend, resume) with a NETWORK role and V3. 3 (paper): guest checkout and PCI DSS scope.
