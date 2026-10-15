package com.ghoomo.rooms;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.time.LocalDate;
import java.util.List;

interface RoomRepository extends JpaRepository<Room, Long> {

    /** Rooms with enough beds and no block overlapping [checkIn, checkOut): the same rule as the overlap check. */
    @Query("""
            select r from Room r
             where r.capacity >= :guests
               and not exists (select b from RoomBlock b
                                where b.roomId = r.id and b.checkIn < :checkOut and b.checkOut > :checkIn)
             order by r.id""")
    List<Room> free(LocalDate checkIn, LocalDate checkOut, int guests);
}
