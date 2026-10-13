package com.dakroute.fleet;

import java.util.List;

/**
 * An interface: "anything that contributes service tasks". It says what, not how, and holds no state.
 * A vehicle is built from several of these (a powertrain and a body), instead of inheriting from a chain of parents.
 */
interface ServiceItems {

    List<ServiceTask> tasks();
}
