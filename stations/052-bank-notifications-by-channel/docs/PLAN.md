# Station 052 plan: Bank notifications by channel

**Problem.** Tijori's 900-line NotificationService wrote and sent SMS, email and push in one method. Two email
changes in March broke SMS: lower-casing the email address threw for customers with no email, before the SMS was
sent; and "Rs" became "₹" in the shared amount format, which takes an SMS out of GSM-7 (70 characters a part, not 160).

**Endpoints.** `POST /notifications` {customerId, type DEBIT_ALERT | NEW_DEVICE_LOGIN | STATEMENT_READY,
amountPaise, merchant} 201 with one delivery per channel (SENT, SKIPPED by preference, UNREACHABLE without an
address, FAILED); 400 malformed, 422 unknown customer or debit without amount. `PUT
/customers/{id}/notification-preferences` {sms, email, push} 200, 400, 404. Demo rules: debit alerts always by SMS;
new-device logins to every reachable channel; statements by preference only. Sending is simulated: an Outbox record.

**Code.** Channel interface (name, deliver); SmsChannel, EmailChannel, PushChannel each own their wording, address
and limits; NotificationService gets List<Channel>, applies the rule per type, isolates failures (one channel's
exception is FAILED, the others still go). Rupees formats paise in Indian groups by hand: DecimalFormat's en-IN
printed 12,345,678.00 (one group size only).

**Tests.** OneClassForAllChannelsTrapTest (old class: no SMS for Rohan; old SMS has ₹ and is over 70 characters;
fixed API: SMS sent, GSM-7, at most 160), NotificationContractTest, ChannelIsolationTest (@MockitoSpyBean email
throws, SMS and push still SENT; rupee grouping). Mutations: no isolation -> 1 red; ₹ in SMS -> 3; preferences
ignored -> 1; western grouping -> 2; email without null check -> 1 (FAILED instead of UNREACHABLE, SMS still sent).

**Practice.** 1: a WhatsApp channel as one new class (the service unchanged). 2: retry only failed deliveries.
Design: when an interface per channel is overkill.
