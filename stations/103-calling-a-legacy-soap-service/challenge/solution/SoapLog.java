package com.bimaly.policies;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.ws.WebServiceMessage;
import org.springframework.ws.client.support.interceptor.ClientInterceptorAdapter;
import org.springframework.ws.context.MessageContext;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.regex.Pattern;

/** Challenge 1: every envelope at DEBUG, for support, with the customer's name masked. */
class SoapLog extends ClientInterceptorAdapter {

    private static final Logger log = LoggerFactory.getLogger(SoapLog.class);
    private static final Pattern NAME = Pattern.compile("(<(?:\\w+:)?customerName>)[^<]*(</)");

    @Override
    public boolean handleRequest(MessageContext context) {
        log("request", context.getRequest());
        return true;
    }

    @Override
    public boolean handleResponse(MessageContext context) {
        log("response", context.getResponse());
        return true;
    }

    @Override
    public boolean handleFault(MessageContext context) {
        log("fault", context.getResponse());
        return true;
    }

    private static void log(String kind, WebServiceMessage message) {
        if (!log.isDebugEnabled()) {
            return;
        }
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        try {
            message.writeTo(out);
        } catch (IOException e) {
            log.debug("SOAP {} could not be written for the log: {}", kind, e.getMessage());
            return;
        }
        log.debug("SOAP {}: {}", kind, NAME.matcher(out.toString(StandardCharsets.UTF_8)).replaceAll("$1***$2"));
    }
}
