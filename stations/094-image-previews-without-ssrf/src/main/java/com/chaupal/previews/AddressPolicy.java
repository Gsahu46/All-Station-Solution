package com.chaupal.previews;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.net.Inet4Address;
import java.net.Inet6Address;
import java.net.InetAddress;
import java.util.List;

/**
 * Which addresses the server may fetch from: the public internet only. Blocked: loopback, private networks, link-local
 * (169.254.0.0/16, where cloud metadata services live), carrier-grade NAT, "this network", multicast and IPv6 unique-local.
 */
@Component
class AddressPolicy {

    private final List<String> allowedPrivate;

    AddressPolicy(@Value("${chaupal.previews.allowed-private-addresses:}") List<String> allowedPrivate) {
        this.allowedPrivate = allowedPrivate;
    }

    boolean isBlocked(InetAddress a) {
        if (allowedPrivate.contains(a.getHostAddress())) {
            return false;
        }
        // No check for IPv6 addresses wrapping IPv4 ones (::ffff:127.0.0.1): Java already turns them into IPv4 addresses.
        if (a instanceof Inet6Address v6 && (v6.getAddress()[0] & 0xFE) == 0xFC) {
            return true;   // fc00::/7, unique local
        }
        if (a instanceof Inet4Address) {
            int first = a.getAddress()[0] & 0xFF;
            int second = a.getAddress()[1] & 0xFF;
            if (first == 0 || (first == 100 && second >= 64 && second <= 127)) {
                return true;   // 0.0.0.0/8 and 100.64.0.0/10
            }
        }
        return a.isAnyLocalAddress() || a.isLoopbackAddress() || a.isLinkLocalAddress() || a.isSiteLocalAddress() || a.isMulticastAddress();
    }
}
