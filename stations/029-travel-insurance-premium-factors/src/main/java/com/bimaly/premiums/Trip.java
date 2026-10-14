package com.bimaly.premiums;

/** What a quote is for: one traveller, one trip. */
record Trip(int age, Destination destination, int days, boolean adventureSports) {

    enum Destination { ASIA, EUROPE, USA_CANADA, WORLDWIDE }
}
