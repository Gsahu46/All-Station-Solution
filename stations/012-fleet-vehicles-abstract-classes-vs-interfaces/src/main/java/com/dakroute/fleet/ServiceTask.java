package com.dakroute.fleet;

/** A maintenance job and how often it is due, in kilometres. */
public record ServiceTask(String name, int everyKm) {
}
