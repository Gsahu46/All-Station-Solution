package com.kartwala.categories;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

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

    @GetMapping("/categories/{id}/children")
    List<CategoryTree.Child> children(@PathVariable long id) {
        return tree.children(id);
    }

    record Move(@NotNull Long parentId) {
    }

    @PutMapping("/categories/{id}/parent")
    CategoryTree.Breadcrumb move(@PathVariable long id, @Valid @RequestBody Move body) {
        return tree.move(id, body.parentId());
    }

    @GetMapping("/categories/{id}/descendants")
    CategoryTree.Descendants descendants(@PathVariable long id) {
        return tree.descendants(id);
    }
}
