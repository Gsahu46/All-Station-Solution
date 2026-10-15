package com.ghoomo.rooms;

import org.springframework.data.repository.Repository;

import java.time.LocalDate;

/** The overlap checks the team tried before, kept only in tests (Spring Data writes their queries too). */
interface OldRoomBlockRepository extends Repository<RoomBlock, Long> {

    /** The original: a stay clashes only if it starts on the same day as another. */
    boolean existsByRoomIdAndCheckInEquals(Long roomId, LocalDate checkIn);   // "Equals": a name ending in "CheckIn" would read "In" as the IN keyword

    /** The first fix: ranges compared with both ends included, as if the check-out night were part of the stay. */
    boolean existsByRoomIdAndCheckInLessThanEqualAndCheckOutGreaterThanEqual(Long roomId, LocalDate newCheckOut, LocalDate newCheckIn);
}
