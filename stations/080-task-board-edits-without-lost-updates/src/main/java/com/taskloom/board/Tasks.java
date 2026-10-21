package com.taskloom.board;

import org.springframework.data.repository.CrudRepository;

interface Tasks extends CrudRepository<Task, Long> {
}
