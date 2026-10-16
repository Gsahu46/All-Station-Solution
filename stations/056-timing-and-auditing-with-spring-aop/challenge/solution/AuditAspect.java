package com.paysetu.payouts;

import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.reflect.MethodSignature;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.util.Arrays;

/**
 * Around every @Audited method: time it, run it, and write one audit event, SUCCESS or FAILURE. It runs in Spring's
 * proxy, so it only sees calls that go through the proxy: public methods called from another bean.
 * Order 0: ahead of the transaction advisor (lowest precedence), so it wraps the transaction and a failed payout's
 * audit event is written after the rollback, not rolled back with it (station 057 goes further). Not
 * HIGHEST_PRECEDENCE: that runs before Spring's ExposeInvocationInterceptor and breaks binding the annotation.
 */
@Aspect
@Component
@Order(0)
class AuditAspect {

    private static final Logger log = LoggerFactory.getLogger(AuditAspect.class);

    private final AuditLog auditLog;

    AuditAspect(AuditLog auditLog) {
        this.auditLog = auditLog;
    }

    @Around("@annotation(audited)")
    Object audit(ProceedingJoinPoint call, Audited audited) throws Throwable {
        MethodSignature signature = (MethodSignature) call.getSignature();
        String method = signature.getDeclaringType().getSimpleName() + "." + signature.getName();
        String subject = subject(signature, call.getArgs(), audited.subjectParam());
        long start = System.nanoTime();
        try {
            Object result = call.proceed();
            finish(audited, "SUCCESS", subject, method, null, start);
            return result;
        } catch (Throwable e) {
            finish(audited, "FAILURE", subject, method, describe(e), start);
            throw e;   // auditing never changes what the caller sees
        }
    }

    private void finish(Audited audited, String outcome, String subject, String method, String error, long start) {
        long ms = (System.nanoTime() - start) / 1_000_000;
        auditLog.record(audited.action(), outcome, subject, method, error, ms, actor());
        log.info("{} {} {} in {} ms", audited.action(), outcome, method, ms);
    }

    /** Only the parameter that was asked for: never every argument, which would copy account numbers into the log. */
    private static String subject(MethodSignature signature, Object[] args, String param) {
        int i = Arrays.asList(signature.getParameterNames()).indexOf(param);
        return i < 0 ? null : String.valueOf(args[i]);
    }

    /** The X-Operator header of the current HTTP request, or "system" outside one (a job, a test, a missing header). */
    private static String actor() {
        if (RequestContextHolder.getRequestAttributes() instanceof ServletRequestAttributes request) {
            String operator = request.getRequest().getHeader("X-Operator");
            if (operator != null && !operator.isBlank()) {
                return operator.strip().length() > 40 ? operator.strip().substring(0, 40) : operator.strip();
            }
        }
        return "system";
    }

    private static String describe(Throwable e) {
        if (e instanceof ErrorResponseException r && r.getBody().getTitle() != null) {
            return r.getBody().getTitle();
        }
        return e.getClass().getSimpleName();
    }
}
