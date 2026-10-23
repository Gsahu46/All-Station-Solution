package com.mapwise.edge;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * What the app believes about the request. Behind the load balancer these come from Tomcat's RemoteIpValve, which
 * rewrites them from the X-Forwarded-* headers, and only when the request really came from the load balancer.
 */
@RestController
class WhoAmIController {

    record WhoAmI(String clientIp, String scheme, boolean secure, String host, int port, String url) {
    }

    @GetMapping("/whoami")
    WhoAmI whoami(HttpServletRequest req) {
        return new WhoAmI(req.getRemoteAddr(), req.getScheme(), req.isSecure(), req.getServerName(), req.getServerPort(), req.getRequestURL().toString());
    }
}
