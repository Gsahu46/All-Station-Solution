package com.safarbus.bookings;

/** A scheduled bus. Every seat costs the same fare (demo rule). */
record Trip(long id, String route, int seats, long farePaise) {
}
