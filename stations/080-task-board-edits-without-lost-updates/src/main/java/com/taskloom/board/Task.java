package com.taskloom.board;

import org.springframework.data.annotation.Id;
import org.springframework.data.annotation.Version;
import org.springframework.data.relational.core.mapping.Table;

/** One card. Spring Data JDBC adds "AND version = ?" to every update and bumps the version when it succeeds. */
@Table("tasks")
record Task(@Id Long id, String board, String title, String description, String status, String assignee, @Version Long version) {
}
