package com.ghoomo.bookings;

/**
 * A validation group: checks that compare fields with each other or with the catalogue. They run only after every
 * field passed on its own (the Default group), and their failures are 422, not 400.
 */
interface Consistency {
}
