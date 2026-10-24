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

    // SOAP 1.1 says Client and Server; SOAP 1.2 says Sender and Receiver.
    private static final Set<String> OUR_FAULT = Set.of("Client", "Sender");
    private final WebServiceTemplate insurer;
    private final Jaxb2Marshaller messages;

    InsurerClient(WebServiceTemplate insurer, Jaxb2Marshaller messages) {
        this.insurer = insurer;
        this.messages = messages;
    }

    IssuePolicyResponse issue(IssuePolicyRequest request) {
        try {
            return (IssuePolicyResponse) insurer.marshalSendAndReceive(request, new SoapActionCallback(SOAP_ACTION));
        } catch (SoapFaultClientException fault) {
            PolicyFault detail = detail(fault);
            boolean ours = false;   // a fault comes from the insurer, so it is the insurer's problem
            throw new Refused(ours, detail == null ? fault.getFaultCode().getLocalPart() : detail.getCode(),
                    detail == null ? fault.getFaultStringOrReason() : detail.getMessage());
        } catch (WebServiceIOException noAnswer) {
            boolean timedOut = false;
            for (Throwable t = noAnswer; t != null; t = t.getCause()) {
                timedOut |= t instanceof HttpTimeoutException;
            }
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
