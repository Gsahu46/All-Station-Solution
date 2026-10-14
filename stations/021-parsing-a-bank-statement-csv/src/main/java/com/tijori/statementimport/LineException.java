package com.tijori.statementimport;

/**
 * One line could not be read. Checked on purpose: every caller of parseLine must decide what a bad line means,
 * and the compiler will not let it forget. Carries the field and the value so the customer can find and fix it.
 */
class LineException extends Exception {

    final String field;
    final String value;

    LineException(String field, String value, String message) {
        super(message);
        this.field = field;
        this.value = value;
    }
}
