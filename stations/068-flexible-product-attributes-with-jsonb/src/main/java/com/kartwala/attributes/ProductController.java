package com.kartwala.attributes;

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
class ProductController {

    /** Demo limits: up to 20 attributes, values up to 40 characters, prices Rs 1 to Rs 1 lakh. */
    record NewProduct(@NotNull @Pattern(regexp = "[A-Za-z0-9-]{3,30}") String sku,
                      @NotBlank @Size(max = 120) String name,
                      @NotNull @Pattern(regexp = "[a-z]{2,30}") String category,
                      @NotNull Long sellerId,
                      @NotNull @Min(100) @Max(10_000_000) Integer pricePaise,
                      @NotNull @Size(max = 20) Map<@Pattern(regexp = "[a-z][a-z_]{1,29}") String, @NotBlank @Size(max = 40) String> attributes) {
    }

    private final ProductCatalog catalog;

    ProductController(ProductCatalog catalog) {
        this.catalog = catalog;
    }

    @PostMapping("/products")
    ResponseEntity<ProductCatalog.Product> create(@Valid @RequestBody NewProduct body) {
        ProductCatalog.Product created = catalog.create(new ProductCatalog.NewProduct(body.sku().toUpperCase(Locale.ROOT), body.name().strip(),
                body.category(), body.sellerId(), body.pricePaise(), body.attributes()));
        return ResponseEntity.created(URI.create("/products/" + created.id())).body(created);
    }

    /** ?category=phones&attr.ram=8GB&attr.storage=128GB: every attr.* pair must match. */
    @GetMapping("/products")
    List<ProductCatalog.Product> search(@RequestParam Map<String, String> params) {
        Map<String, String> wanted = new TreeMap<>();
        params.forEach((key, value) -> {
            if (key.startsWith("attr.")) {
                wanted.put(key.substring(5), value);
            } else if (!key.equals("category")) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Unknown parameter " + key);
            }
        });
        if (wanted.isEmpty() || wanted.size() > 10) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Give 1 to 10 attr.<name>=<value> filters");
        }
        return catalog.search(params.get("category"), wanted);
    }
}
