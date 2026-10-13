package com.kartwala.search;

import java.util.List;

/** The products to suggest. Fixed for this station; a real catalogue has lakhs of rows in a database. */
final class ProductCatalog {

    static final List<Product> PRODUCTS = List.of(
            new Product(1, "Samsung Galaxy M35 5G", 9800),
            new Product(2, "Samsung Galaxy S24", 7600),
            new Product(3, "Samsung 55-inch Crystal TV", 3100),
            new Product(4, "Sambar Masala 100g", 5400),
            new Product(5, "Samosa Party Pack", 1200),
            new Product(6, "SanDisk 128GB Pen Drive", 6900),
            new Product(7, "Safari Suitcase Medium", 2500),
            new Product(8, "Saffola Gold Oil 1L", 8800, false), // challenge 2: out of stock
            new Product(9, "Balsamic Vinegar 500ml", 300),
            new Product(10, "Galaxy Chocolate Bar", 2200),
            new Product(11, "Redmi Note 13", 9100),
            new Product(12, "Realme Narzo 70", 5000),
            new Product(13, "boAt Airdopes 141", 9900),
            new Product(14, "boAt Rockerz 450", 6100),
            new Product(15, "Apple iPhone 15", 8700),
            new Product(16, "Apple AirPods Pro", 4300),
            new Product(17, "OnePlus Nord CE4", 7000),
            new Product(18, "Parle-G Biscuits", 9500),
            new Product(19, "Tata Salt 1kg", 9700),
            new Product(20, "Tata Tea Gold 500g", 6400),
            new Product(21, "Maggi Noodles 12 Pack", 9300),
            new Product(22, "Dettol Handwash", 5100),
            new Product(23, "Philips Trimmer BT3221", 4800),
            new Product(24, "Prestige Pressure Cooker 5L", 4100),
            new Product(25, "Head & Shoulders Shampoo", 4500),
            new Product(26, "Classmate Notebook", 3600));

    private ProductCatalog() {
    }
}
