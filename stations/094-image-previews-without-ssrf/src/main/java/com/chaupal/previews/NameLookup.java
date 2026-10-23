package com.chaupal.previews;

import java.net.InetAddress;
import java.net.UnknownHostException;

/** DNS, as one method, so tests can stand in for it (names that resolve to test servers, or that change their answer). */
@FunctionalInterface
interface NameLookup {

    InetAddress[] lookup(String host) throws UnknownHostException;
}
