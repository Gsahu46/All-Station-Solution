package com.parkora.parking;

/**
 * An enum with data: each vehicle type knows which slot it needs and what it pays.
 * Fees are whole paise. The rates are demo rules for this station, not any city's parking tariff.
 */
public enum VehicleType {
    BIKE(SlotType.BIKE, 2_000, 1_000),  // Rs 20 for the first hour, Rs 10 for each hour after
    CAR(SlotType.CAR, 4_000, 3_000);    // Rs 40 for the first hour, Rs 30 for each hour after

    final SlotType slotType;
    final int firstHourPaise;
    final int extraHourPaise;

    VehicleType(SlotType slotType, int firstHourPaise, int extraHourPaise) {
        this.slotType = slotType;
        this.firstHourPaise = firstHourPaise;
        this.extraHourPaise = extraHourPaise;
    }
}
