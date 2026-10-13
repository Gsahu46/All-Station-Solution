package com.chaupal.comments;

/** A post. A private post and its comments are visible to its author only. */
record Post(long id, String author, String title, boolean isPrivate) {

    boolean visibleTo(String user) {
        return !isPrivate || author.equals(user);
    }
}
