package com.kartwala.refunds;

import java.util.List;

/**
 * Replays the ticket's request (KW-1042, line L2) on the old code and prints the exception the way the log showed it,
 * keeping only this app's frames. Run by docs/capture.sh, so the stack trace on the page is a real one.
 */
public class TicketReplay {

    public static void main(String[] args) {
        OldOrder order = new OldOrder("KW-1042", List.of(new Line("L1", "Denim jeans", 199_900), new Line("L2", "Leather belt", 59_900)), null);
        try {
            OldRefundCalculator.refundable(order, List.of(order.lines().get(1)));
        } catch (NullPointerException e) {
            System.out.println(e);
            for (StackTraceElement frame : e.getStackTrace()) {
                if (frame.getClassName().startsWith("com.kartwala")) {
                    System.out.println("\tat " + frame);
                }
            }
        }
    }
}
