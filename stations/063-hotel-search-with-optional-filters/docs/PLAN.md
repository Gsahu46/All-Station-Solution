# Station 063 plan: Hotel search with optional filters

**Problem.** Ghoomo's hotel search glued optional filters into one SQL string. A quote in the city turned the filter
off; the sort parameter could run a second statement; joining amenities gave duplicates and "any of" instead of "all
of".

**Endpoint.** `GET /hotels?city&minPrice&maxPrice&stars&amenities&sort&page&size`, every filter optional. City
`[A-Za-z-]{3,30}` lower-cased; prices whole rupees in the query (x100 to paise); stars list 1-5; amenities up to 5
codes, lower-cased, all must match, unknown -> 400; sort whitelist price, -price, stars, -stars, name (id last);
page 0-100, size 1-50. 200 {total, page, sort, hotels[{id, name, city, stars, pricePerNightPaise, amenities}]};
no match: total 0. minPrice > maxPrice: 400.

**Code.** One Specification per filter (HotelSpecs), combined with Specification.allOf; amenities as EXISTS
subqueries; findAll(spec, pageable) with @EntityGraph(amenities).

**Database.** hotels_city_shape, hotels_stars_range, hotels_price_range (Rs 500 to Rs 1 lakh, demo), hotels_name_per_city,
hotel_amenities_pk + FKs (cascade from hotel). Index hotels (city, price), hotel_amenities (amenity_code, hotel_id).

**Found while building.** (1) The injected UPDATE needed `--` to comment out the appended LIMIT; then PostgreSQL ran
it and the caller only saw "Multiple ResultSets were returned by the query." (2) Passing the user's sort straight to
Sort.by: Spring Data refused "name; DELETE ..." ("Sort expression ... must only contain property references") but as a
500, and "price" as a 500 "No property 'price' found for type 'Hotel'". (3) Removing the entity graph turned nothing
red: no test counts queries here (station 061 does).

**Mutations.** sort straight to Sort.by -> 2; amenities any-of -> 3; no lower-casing -> 1; rupees as paise -> 2;
no min/max check -> 1; no amenity check -> 1; no entity graph -> 0.

**Practice.** 1: q name search with LIKE escaping. 2: stars facet (the same specs minus stars, Criteria GROUP BY).
3 (paper): when Specifications stop being enough (search engine).
