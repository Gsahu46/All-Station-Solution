package com.taskloom.welcome;

/** Published inside the sign-up transaction. What it causes is up to the listeners, and when: before or after commit. */
record SignedUp(long signupId, String email, String name) {
}
