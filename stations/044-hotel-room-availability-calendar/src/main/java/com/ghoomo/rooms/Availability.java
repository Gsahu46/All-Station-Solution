package com.ghoomo.rooms;

import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.dao.PessimisticLockingFailureException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.ErrorResponseException;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

@Service
class Availability {

    record Night(LocalDate date, boolean available) {
    }

    record Calendar(long roomId, LocalDate from, LocalDate to, int freeNights, List<Night> nights) {
    }

    record BlockView(long id, long roomId, LocalDate checkIn, LocalDate checkOut, long nights, String guestName) {
        static BlockView of(RoomBlock b) {
            return new BlockView(b.getId(), b.getRoomId(), b.getCheckIn(), b.getCheckOut(),
                    b.getCheckIn().datesUntil(b.getCheckOut()).count(), b.getGuestName());
        }
    }

    private final RoomRepository rooms;
    private final RoomBlockRepository blocks;

    Availability(RoomRepository rooms, RoomBlockRepository blocks) {
        this.rooms = rooms;
        this.blocks = blocks;
    }

    /** The nights from `from` up to, not including, `to`: the same half-open rule as a stay. */
    @Transactional(readOnly = true)
    Calendar calendar(long roomId, LocalDate from, LocalDate to) {
        requireRoom(roomId);
        List<RoomBlock> overlapping = blocks.findByRoomIdAndCheckInBeforeAndCheckOutAfterOrderByCheckIn(roomId, to, from);
        List<Night> nights = new ArrayList<>();
        for (LocalDate night = from; night.isBefore(to); night = night.plusDays(1)) {
            LocalDate n = night;
            nights.add(new Night(n, overlapping.stream().noneMatch(b -> b.holds(n))));
        }
        return new Calendar(roomId, from, to, (int) nights.stream().filter(Night::available).count(), nights);
    }

    /**
     * The friendly check first (a clear 409 for the usual case), then the insert. Two requests can both pass the
     * check at the same moment; the database's room_blocks_no_overlap lets only one insert win, and the other
     * becomes the same 409, not a 500, whether it was refused by the constraint or aborted as a deadlock.
     */
    @Transactional
    BlockView block(long roomId, LocalDate checkIn, LocalDate checkOut, String guestName) {
        requireRoom(roomId);
        if (blocks.existsByRoomIdAndCheckInBeforeAndCheckOutAfter(roomId, checkOut, checkIn)) {
            throw taken(roomId, checkIn, checkOut);
        }
        try {
            return BlockView.of(blocks.saveAndFlush(new RoomBlock(roomId, checkIn, checkOut, guestName)));
        } catch (DataIntegrityViolationException e) {
            if (String.valueOf(e.getMessage()).contains("room_blocks_no_overlap")) {
                throw taken(roomId, checkIn, checkOut);
            }
            throw e;
        } catch (PessimisticLockingFailureException e) {
            // Two overlapping inserts can each wait for the other's exclusion check: PostgreSQL then aborts one as a
            // deadlock (found by BlockConcurrencyTest). The other commits its nights, so this request did clash.
            throw taken(roomId, checkIn, checkOut);
        }
    }

    private void requireRoom(long roomId) {
        if (!rooms.existsById(roomId)) {
            throw problem(HttpStatus.NOT_FOUND, "Room not found", "No room " + roomId + ".");
        }
    }

    private static ErrorResponseException taken(long roomId, LocalDate checkIn, LocalDate checkOut) {
        return problem(HttpStatus.CONFLICT, "Not available", "Room " + roomId + " is already held for a night between " + checkIn + " and " + checkOut + ".");
    }

    static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setTitle(title);
        return new ErrorResponseException(status, p, null);
    }
}
