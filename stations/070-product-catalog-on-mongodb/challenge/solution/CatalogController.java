package com.kartwala.catalog;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.net.URI;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.TreeMap;

@RestController
class CatalogController {

    /** The same rules as the collection's validator, checked first for a clear 400. Demo limits. */
    record NewProduct(@NotNull @Pattern(regexp = "[A-Za-z0-9-]{3,30}") String sku,
                      @NotBlank @Size(max = 120) String name,
                      @NotNull @Pattern(regexp = "[a-z]{2,30}") String category,
                      @NotNull Long sellerId,
                      @NotNull @Min(100) @Max(10_000_000) Integer pricePaise,
                      @NotNull @Size(max = 20) Map<@Pattern(regexp = "[a-z][a-z_]{1,29}") String, @NotBlank @Size(max = 40) String> attributes) {
    }

    private static final java.util.regex.Pattern ATTRIBUTE = java.util.regex.Pattern.compile("[a-z][a-z_]{1,29}");

    private final Catalog catalog;

    CatalogController(Catalog catalog) {
        this.catalog = catalog;
    }

    @PostMapping("/catalog/products")
    ResponseEntity<CatalogProduct> create(@Valid @RequestBody NewProduct body) {
        CatalogProduct created = catalog.create(new CatalogProduct(null, body.sku().toUpperCase(Locale.ROOT), body.name().strip(), body.category(),
                body.sellerId(), body.pricePaise(), body.attributes()));
        return ResponseEntity.created(URI.create("/catalog/products/" + created.id())).body(created);
    }

    @GetMapping("/catalog/products/{id}")
    CatalogProduct byId(@PathVariable String id) {
        return catalog.byId(id);
    }

    @GetMapping("/catalog/facets")
    Map<String, Integer> facets(@RequestParam @jakarta.validation.constraints.Pattern(regexp = "[a-z]{2,30}") String category,
                                @RequestParam @jakarta.validation.constraints.Pattern(regexp = "[a-z][a-z_]{1,29}") String facet) {
        return catalog.facet(category, facet);
    }

    /** ?category=phones&attr.ram=8GB: every attr.* filter must match. */
    @GetMapping("/catalog/products")
    List<CatalogProduct> search(@RequestParam Map<String, String> params) {
        Map<String, String> attributes = new TreeMap<>();
        params.forEach((key, value) -> {
            if (key.startsWith("attr.") && ATTRIBUTE.matcher(key.substring(5)).matches()) {
                attributes.put(key.substring(5), value);
            } else if (!key.equals("category")) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Unknown parameter " + key);
            }
        });
        String category = params.get("category");
        if (category != null && !category.matches("[a-z]{2,30}")) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Not a category: " + category);
        }
        if (category == null && attributes.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Give a category or at least one attr.<name>=<value>");
        }
        return catalog.search(category, attributes);
    }
}
