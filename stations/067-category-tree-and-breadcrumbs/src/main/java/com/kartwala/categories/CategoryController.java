package com.kartwala.categories;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

@RestController
class CategoryController {

    private final CategoryTree tree;

    CategoryController(CategoryTree tree) {
        this.tree = tree;
    }

    @GetMapping("/categories/{id}/breadcrumb")
    CategoryTree.Breadcrumb breadcrumb(@PathVariable long id) {
        return tree.breadcrumb(id);
    }

    @GetMapping("/categories/{id}/descendants")
    CategoryTree.Descendants descendants(@PathVariable long id) {
        return tree.descendants(id);
    }
}
