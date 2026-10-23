# Station 097 plan: Behind a load balancer

**Problem.** Mapwise (fictional): behind the load balancer every request seemed to come from one address (the
balancer's), links in Location headers pointed to http://10.0.0.17:8080/, and uploads timed out at 60 s. The first
fix read X-Forwarded-For directly: any client could write the office's address into it and reach /admin.

**Endpoints.** `GET /whoami` (public): what the app believes: client address, scheme, secure, host, port, URL.
`POST /uploads` (HTTP Basic): the raw body streamed, counted and hashed (simulated storage, bytes not kept), at most
10 MiB (413), 201 with Location. `GET /uploads/{id}`: own only, else 404. `GET /admin/uploads`: ADMIN and from the
office network 203.0.113.0/24 (demo rule), else 403.

**Forward headers.** `server.forward-headers-strategy: native`: Tomcat's RemoteIpValve rewrites remote address,
scheme, host and port from X-Forwarded-*, only for requests from `internal-proxies` (10.0.0.0/24 here; Boot 4.1.1's
default is every private and loopback range), walking X-Forwarded-For from the right and stopping at the first
address that is not a trusted proxy.

**Timeouts at every hop.** Client to balancer: the balancer's idle timeout (60 s). Balancer to app: Tomcat's
connection-timeout 20 s (a stalled upload is answered 408 and its thread freed) and keep-alive 75 s (longer than the
balancer's idle, so the app never closes a connection the balancer is about to reuse). No session (STATELESS), so no
sticky sessions.

**Trap.** `SpoofedClientIpTrapTest`: the first X-Forwarded-For entry is whatever the client wrote. The API: a direct
client's header ignored; through the balancer, the balancer's entry. `DefaultTrustedProxiesTrapTest`: with Boot's
default list, a machine at 127.0.0.2 (not the balancer) is trusted and reaches /admin.

**Tests.** A real port (the valve runs in Tomcat, not in MockMvc). The balancer is 127.0.0.1, a direct client
127.0.0.2 (HttpClient localAddress). Tests use a 1 s read timeout and a 1 MiB upload limit.

**Review.** The admin check reads X-Forwarded-For's first entry; Location built from "http://" + Host.

**Practice.** 1: X-Request-Id, the balancer's kept, a client's replaced. 2: 3 uploads a minute per client address.
3 (paper): uploads that take longer than any timeout (direct to object storage).
