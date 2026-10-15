package com.ghoomo.rooms;

import org.springframework.data.jpa.repository.JpaRepository;

import java.time.LocalDate;
import java.util.List;

/**
 * Two half-open ranges [a, b) and [c, d) overlap exactly when a < d and b > c. With "existing" on the left:
 * existing.checkIn < new.checkOut AND existing.checkOut > new.checkIn. Spring Data writes it from the method name:
 * CheckInBefore(x) is check_in < x, CheckOutAfter(y) is check_out > y.
 */
interface RoomBlockRepository extends JpaRepository<RoomBlock, Long> {

    boolean existsByRoomIdAndCheckInBeforeAndCheckOutAfter(Long roomId, LocalDate newCheckOut, LocalDate newCheckIn);

    List<RoomBlock> findByRoomIdAndCheckInBeforeAndCheckOutAfterOrderByCheckIn(Long roomId, LocalDate to, LocalDate from);
}
