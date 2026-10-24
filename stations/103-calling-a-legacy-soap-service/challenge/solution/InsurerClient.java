package com.bimaly.policies;

import com.bimaly.policies.insurer.IssuePolicyRequest;
import com.bimaly.policies.insurer.IssuePolicyResponse;
import com.bimaly.policies.insurer.PolicyFault;
import org.springframework.oxm.jaxb.Jaxb2Marshaller;
import org.springframework.stereotype.Component;
import org.springframework.ws.client.WebServiceIOException;
import org.springframework.ws.client.core.WebServiceTemplate;
import org.springframework.ws.soap.SoapFaultDetailElement;
import org.springframework.ws.soap.client.SoapFaultClientException;
import org.springframework.ws.soap.client.core.SoapActionCallback;

import java.io.IOException;
import java.net.http.HttpTimeoutException;
import java.util.Iterator;
import java.util.Set;

/** Calls the insurer's IssuePolicy operation and turns what can go wrong into three plain outcomes. */
@Component
class InsurerClient {

    static final String SOAP_ACTION = "http://insurer.example/policy/v1/IssuePolicy";

    /** The insurer answered with a SOAP fault. Its own fault code and message, and whose mistake it says it is. */
    static final class Refused extends RuntimeException {
        final boolean ourRequest;
        final String code;

        Refused(boolean ourRequest, String code, String message) {
            super(message);
            this.ourRequest = ourRequest;
            this.code = code;
        }
    }

    /** No answer: the insurer could not be reached, or did not answer in time. */
    static final class Unreachable extends RuntimeException {
        final boolean timedOut;

        Unreachable(boolean timedOut, Throwable cause) {
            super(cause);
            this.timedOut = timedOut;
        }
    }

    /** Challenge 2: too many failures in a row; the insurer is left alone for a while. */
    static final class CircuitOpen extends RuntimeException {
    }

    static final int FAILURES_TO_OPEN = 3;
    private final java.util.concurrent.atomic.AtomicInteger failuresInARow = new java.util.concurrent.atomic.AtomicInteger();
    private volatile long closedAgainAt;   // System.nanoTime()
    private final java.time.Duration coolDown;

    // SOAP 1.1 says Client and Server; SOAP 1.2 says Sender and Receiver.
    private static final Set<String> OUR_FAULT = Set.of("Client", "Sender");
    private final WebServiceTemplate insurer;
    private final Jaxb2Marshaller messages;

    InsurerClient(WebServiceTemplate insurer, Jaxb2Marshaller messages,
                  @org.springframework.beans.factory.annotation.Value("${bimaly.insurer.cool-down:30s}") java.time.Duration coolDown) {
        this.insurer = insurer;
        this.messages = messages;
        this.coolDown = coolDown;
    }

    private void failed() {
        if (failuresInARow.incrementAndGet() >= FAILURES_TO_OPEN) {
            closedAgainAt = System.nanoTime() + coolDown.toNanos();
            failuresInARow.set(0);
        }
    }

    IssuePolicyResponse issue(IssuePolicyRequest request) {
        if (System.nanoTime() - closedAgainAt < 0) {
            throw new CircuitOpen();
        }
        try {
            IssuePolicyResponse response = (IssuePolicyResponse) insurer.marshalSendAndReceive(request, new SoapActionCallback(SOAP_ACTION));
            failuresInARow.set(0);
            return response;
        } catch (SoapFaultClientException fault) {
            PolicyFault detail = detail(fault);
            boolean ours = OUR_FAULT.contains(fault.getFaultCode().getLocalPart());
            if (ours) {
                failuresInARow.set(0);   // a refusal is the insurer working
            } else {
                failed();
            }
            throw new Refused(ours, detail == null ? fault.getFaultCode().getLocalPart() : detail.getCode(),
                    detail == null ? fault.getFaultStringOrReason() : detail.getMessage());
        } catch (WebServiceIOException noAnswer) {
            boolean timedOut = false;
            for (Throwable t = noAnswer; t != null; t = t.getCause()) {
                timedOut |= t instanceof HttpTimeoutException;
            }
            failed();
            throw new Unreachable(timedOut, noAnswer);
        }
    }

    /** The PolicyFault the WSDL declares, if the insurer sent one in the fault's detail. */
    private PolicyFault detail(SoapFaultClientException fault) {
        if (fault.getSoapFault().getFaultDetail() == null) {
            return null;
        }
        Iterator<SoapFaultDetailElement> entries = fault.getSoapFault().getFaultDetail().getDetailEntries();
        try {
            return entries.hasNext() && messages.unmarshal(entries.next().getSource()) instanceof PolicyFault p ? p : null;
        } catch (RuntimeException notOurs) {
            return null;
        }
    }
}
