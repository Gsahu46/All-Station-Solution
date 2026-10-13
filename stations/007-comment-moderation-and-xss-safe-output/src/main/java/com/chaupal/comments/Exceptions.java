package com.chaupal.comments;

/** What can go wrong, in business terms. ApiErrors turns each into a problem response. */
final class Exceptions {

    private Exceptions() {
    }

    /** 404. Also for a private post the user may not see: the API does not confirm it exists. */
    static class PostNotFound extends RuntimeException {
    }

    /** 422. The text contains a banned word. The response does not say which one. */
    static class BreaksCommunityRules extends RuntimeException {
    }

    /** 429. Too many comments in the window. */
    static class TooManyComments extends RuntimeException {
    }
}
