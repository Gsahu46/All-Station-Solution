package com.paysetu.payouts;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * Marks a public method of a Spring bean whose every call is timed and written to the audit log, success or
 * failure. One line on the method replaces the copy-pasted timing and audit code.
 */
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface Audited {

    /** What happened, in business words: PAYOUT_REQUESTED. */
    String action();

    /** The name of the parameter that says who it happened to (its value is recorded), or "" for none. */
    String subjectParam() default "";
}
