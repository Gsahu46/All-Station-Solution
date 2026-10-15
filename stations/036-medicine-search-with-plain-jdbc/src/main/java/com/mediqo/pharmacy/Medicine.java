package com.mediqo.pharmacy;

/** One product in the catalogue, as the search returns it. */
record Medicine(long id, String name, String strength, String form, long pricePaise, boolean prescriptionRequired) {
}
