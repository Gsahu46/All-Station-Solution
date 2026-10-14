package com.tijori.otp;

/** Sends one SMS. The real one calls an SMS provider; this station uses a simulated one. */
interface SmsSender {

    void send(String mobile, String text);
}
