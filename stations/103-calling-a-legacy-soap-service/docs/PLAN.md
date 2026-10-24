# Station 103 plan: Calling a legacy SOAP service

**Problem.** Bimaly (fictional insurance broker) must issue policies through the insurer's 15-year-old SOAP service.
Nobody on the team has used SOAP. The first client used Spring-WS's defaults: a slow insurer held each request for up
to a minute, and every SOAP fault, even "we do not sell that product", reached the customer as a 500.

**Endpoint.** `POST /policies {customerName, dateOfBirth, productCode, sumInsuredPaise}`: 201 with the insurer's
policy number and premium; 400 bad input (never sent to the insurer); 422 the insurer refused (its code and reason);
502 the insurer's system failed or could not be reached; 504 no answer within 8 s ("may or may not have been issued").

**Fix.** Classes generated from the insurer's WSDL at build time (jaxb-maven-plugin). WebServiceTemplate with
JdkHttpClientMessageSender: connect 2 s, whole request 8 s. SOAPAction sent. Faults read: Client/Sender = our
request (422, detail unmarshalled to PolicyFault), Server/Receiver = theirs (502). Never retried: IssuePolicy is not
idempotent. No database: the insurer keeps the policies.

**Trap.** `LegacySoapTrapTest`: the default sender's read timeout is 60 s (read by reflection), and an old client is
still waiting after 2 s while the API answered 504 after 1 s; a fault escapes the old way as SoapFaultClientException.

**Review.** Default sender and every fault treated as the insurer's (502).

**Practice.** 1: log the envelopes with the customer's name masked. 2: a circuit breaker after three failures.
3 (paper): finding out what happened to a 504.

**Simulation.** The insurer is simulated (TestInsurer in tests, docs/test-insurer.py in captures).
