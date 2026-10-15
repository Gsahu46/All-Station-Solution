package com.kartwala.refunds;

/** Why the customer wants to return. "Customer's choice" reasons pay the pickup fee; the others are Kartwala's fault. */
enum Reason {
    DAMAGED(false), WRONG_ITEM(false), NOT_AS_DESCRIBED(false), CHANGED_MIND(true), SIZE_ISSUE(true);

    final boolean customersChoice;

    Reason(boolean customersChoice) {
        this.customersChoice = customersChoice;
    }
}
