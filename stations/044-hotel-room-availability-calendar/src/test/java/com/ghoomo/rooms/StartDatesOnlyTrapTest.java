package com.ghoomo.rooms;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.springframework.beans.factory.annotation.Autowired;

import java.time.LocalDate;

import static org.assertj.core.api.Assertions.assertThat;

/** The first test written for this station. Room 101 is held 10-12 June. */
class StartDatesOnlyTrapTest extends ApiTest {

    static final LocalDate JUNE_11 = LocalDate.of(2026, 6, 11);
    static final LocalDate JUNE_12 = LocalDate.of(2026, 6, 12);
    static final LocalDate JUNE_13 = LocalDate.of(2026, 6, 13);
    static final LocalDate JUNE_14 = LocalDate.of(2026, 6, 14);

    @Autowired
    OldRoomBlockRepository old;

    @Test
    void comparingStartDatesSaysElevenToThirteenIsFree() {
        assertThat(old.existsByRoomIdAndCheckInEquals(101L, JUNE_11)).isFalse();                                  // sold again
        assertThat(blocks.existsByRoomIdAndCheckInBeforeAndCheckOutAfter(101L, JUNE_13, JUNE_11)).isTrue();  // the night of the 11th is taken
    }

    @Test
    void includingTheCheckOutDayRefusesABackToBackStay() {
        assertThat(old.existsByRoomIdAndCheckInLessThanEqualAndCheckOutGreaterThanEqual(101L, JUNE_14, JUNE_12)).isTrue();   // wrongly "taken"
        assertThat(blocks.existsByRoomIdAndCheckInBeforeAndCheckOutAfter(101L, JUNE_14, JUNE_12)).isFalse();                  // in on the 12th, as Asha leaves
    }

    @ParameterizedTest(name = "{0} to {1} against 10-12 June -> overlaps {2}")
    @CsvSource({
            "2026-06-11, 2026-06-13, true",    // starts inside
            "2026-06-08, 2026-06-11, true",    // ends inside
            "2026-06-10, 2026-06-12, true",    // the same stay
            "2026-06-10, 2026-06-11, true",    // within, same start
            "2026-06-08, 2026-06-14, true",    // covers it
            "2026-06-08, 2026-06-10, false",   // leaves the morning Asha arrives
            "2026-06-12, 2026-06-14, false",   // arrives the morning Asha leaves
            "2026-06-20, 2026-06-22, false"})  // nowhere near
    void theOverlapRuleOnEveryShape(LocalDate checkIn, LocalDate checkOut, boolean overlaps) {
        assertThat(blocks.existsByRoomIdAndCheckInBeforeAndCheckOutAfter(101L, checkOut, checkIn)).isEqualTo(overlaps);
    }
}
