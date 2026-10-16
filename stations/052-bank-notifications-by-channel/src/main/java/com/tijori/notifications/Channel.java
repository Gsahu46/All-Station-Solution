package com.tijori.notifications;

/**
 * The one thing the notification service needs from a channel. Each implementation owns its wording, its length
 * limits and its address; a change to one cannot reach the others. Small on purpose: two methods.
 */
interface Channel {

    Model.ChannelName name();

    /** Writes and records the message, or answers UNREACHABLE when the customer has no address on this channel. */
    Model.Delivery deliver(Model.Customer customer, Model.Notice notice);
}
