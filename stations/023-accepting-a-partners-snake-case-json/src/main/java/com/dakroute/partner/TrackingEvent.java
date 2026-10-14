package com.dakroute.partner;

import java.time.Instant;

/** Our own shape for a tracking event: camelCase, every time an exact instant in UTC. */
record TrackingEvent(String awbNumber, Status status, String partnerStatusCode, Instant at, String city, String pinCode,
                     Instant promisedBy) {

    /** Our statuses, each with the partner's code for it. A code we do not know yet is UNKNOWN, kept with its raw code. */
    enum Status {
        PICKED_UP("PKD"), IN_TRANSIT("ITR"), OUT_FOR_DELIVERY("OFD"), DELIVERED("DLV"), RETURNING("RTO"), UNKNOWN(null);

        final String partnerCode;

        Status(String partnerCode) {
            this.partnerCode = partnerCode;
        }

        static Status fromPartner(String code) {
            for (Status s : values()) {
                if (code.equals(s.partnerCode)) {
                    return s;
                }
            }
            return UNKNOWN;
        }
    }
}
