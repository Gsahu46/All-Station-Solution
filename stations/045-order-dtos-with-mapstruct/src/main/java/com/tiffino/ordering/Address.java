package com.tiffino.ordering;

import jakarta.persistence.Column;
import jakarta.persistence.Embeddable;

/** Part of the orders row, as a value: no table of its own. */
@Embeddable
public class Address {

    @Column(name = "address_line")
    private String line;
    private String city;
    private String pincode;

    public String getLine() {
        return line;
    }

    public void setLine(String line) {
        this.line = line;
    }

    public String getCity() {
        return city;
    }

    public void setCity(String city) {
        this.city = city;
    }

    public String getPincode() {
        return pincode;
    }

    public void setPincode(String pincode) {
        this.pincode = pincode;
    }
}
