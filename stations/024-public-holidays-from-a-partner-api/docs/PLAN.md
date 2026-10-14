# Station 024 plan: Public holidays from a partner API

**Problem.** Teamdesk's leave balances ignore public holidays. The first attempt called the holiday provider with a
plain RestClient: no timeout (a slow provider holds our threads) and no error handling (its 500 became ours).

**Endpoint.** `GET /holidays?year&state` 200 holidays sorted by date in our shape; 400 bad year or state (no call
made); 404 the provider has no list; 502 provider failed, rejected our key or sent unreadable data, or hung up;
504 provider too slow. The provider's error text is logged, never returned.

**Data.** No database. `@HttpExchange` interface `HolidayProviderClient` built by `HttpServiceProxyFactory` over a
`RestClient` with `JdkClientHttpRequestFactory` (connect 1s, read 2s). A simulated provider in the same app
(`/demo-provider`, demo switches 2098 slow, 2099 fails, TN 404). Tests use a JDK HttpServer stub on a random port.

**Trap.** `SlowProviderTrapTest`: old call waits 2 s; old call throws InternalServerError; the fixed endpoint gives
504 within 1.5 s and 502. Mutations: no read timeout -> 1 red; no RestClientException catch -> 4 red; passing the
provider's message through -> 2 red.

**Tests.** Trap, `HolidayContractTest`, `ProviderFailureTest` (500, 401, bad JSON, hang-up; no internals leak).

**Practice.** 1: serve the last good answer. 2: API key header from configuration. Design: retries and circuit breakers.
