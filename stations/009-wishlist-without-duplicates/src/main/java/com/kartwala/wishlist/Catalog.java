package com.kartwala.wishlist;

import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.Optional;

/** The products that can be wished for. A HashMap keyed by Sku: lookups work because Sku has value equality. */
@Component
class Catalog {

    record Product(Sku sku, String name, int pricePaise) {
    }

    private final Map<Sku, Product> products = Map.of(
            new Sku("PH-12"), new Product(new Sku("PH-12"), "Samsung Galaxy M35 5G", 1_699_900),
            new Sku("TV-55"), new Product(new Sku("TV-55"), "Samsung 55-inch Crystal TV", 4_299_000),
            new Sku("EB-141"), new Product(new Sku("EB-141"), "boAt Airdopes 141", 129_900),
            new Sku("MI-11X"), new Product(new Sku("MI-11X"), "Redmi Note 13", 1_799_900),
            new Sku("CK-5L"), new Product(new Sku("CK-5L"), "Prestige Pressure Cooker 5L", 249_900));

    Optional<Product> find(Sku sku) {
        return Optional.ofNullable(products.get(sku));
    }
}
