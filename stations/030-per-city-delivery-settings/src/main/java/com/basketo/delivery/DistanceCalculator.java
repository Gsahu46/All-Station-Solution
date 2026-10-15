package com.basketo.delivery;

/** Kilometres between two points. A road-distance service could replace the default without touching callers. */
@FunctionalInterface
interface DistanceCalculator {

    double km(DeliverySettings.Location from, double lat, double lon);
}
