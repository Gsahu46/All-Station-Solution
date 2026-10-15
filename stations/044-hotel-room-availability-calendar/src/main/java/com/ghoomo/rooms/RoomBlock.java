package com.ghoomo.rooms;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.LocalDate;

/** A room held for the nights checkIn up to, not including, checkOut. */
@Entity
@Table(name = "room_blocks")
public class RoomBlock {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private Long roomId;
    private LocalDate checkIn;
    private LocalDate checkOut;
    private String guestName;

    protected RoomBlock() {   // for JPA
    }

    RoomBlock(Long roomId, LocalDate checkIn, LocalDate checkOut, String guestName) {
        this.roomId = roomId;
        this.checkIn = checkIn;
        this.checkOut = checkOut;
        this.guestName = guestName;
    }

    public Long getId() {
        return id;
    }

    public Long getRoomId() {
        return roomId;
    }

    public LocalDate getCheckIn() {
        return checkIn;
    }

    public LocalDate getCheckOut() {
        return checkOut;
    }

    public String getGuestName() {
        return guestName;
    }

    /** Is this night (the night starting on that date) held by the block? */
    boolean holds(LocalDate night) {
        return !night.isBefore(checkIn) && night.isBefore(checkOut);
    }
}
