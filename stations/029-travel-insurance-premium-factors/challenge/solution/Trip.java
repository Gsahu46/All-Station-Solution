package com.bimaly.premiums;

/** What a quote is for: one traveller, one trip. */
record Trip(int age, Destination destination, int days, boolean adventureSports, boolean preExistingCondition) {

    /** Challenge 1: callers that do not know about conditions keep working. */
    Trip(int age, Destination destination, int days, boolean adventureSports) {
        this(age, destination, days, adventureSports, false);
    }

    enum Destination { ASIA, EUROPE, USA_CANADA, WORLDWIDE }
}
