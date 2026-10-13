package com.parkora.parking;

/**
 * An enum with data: each vehicle type knows which slot it needs and what it pays.
 * Fees are whole paise. The rates are demo rules for this station, not any city's parking tariff.
 */
public enum VehicleType {
    BIKE(SlotType.BIKE, 2_000, 1_000, 15_000),  // Rs 20 first hour, Rs 10 each hour after, at most Rs 150 a day
    CAR(SlotType.CAR, 4_000, 3_000, 30_000);    // Rs 40 first hour, Rs 30 each hour after, at most Rs 300 a day

    final SlotType slotType;
    final int firstHourPaise;
    final int extraHourPaise;
    final int dailyCapPaise; // challenge 2

    VehicleType(SlotType slotType, int firstHourPaise, int extraHourPaise, int dailyCapPaise) {
        this.slotType = slotType;
        this.firstHourPaise = firstHourPaise;
        this.extraHourPaise = extraHourPaise;
        this.dailyCapPaise = dailyCapPaise;
    }
}
