package com.chhotu.links;

import org.springframework.stereotype.Component;

import java.security.SecureRandom;

/**
 * Seven random base62 characters: 62^7, about 3.5 lakh crore codes. Random, so codes cannot be guessed one from the
 * next; collisions are rare but possible, and the database's primary key turns them into a retry, never an overwrite.
 */
@Component
class CodeGenerator {

    static final String BASE62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";
    static final int LENGTH = 7;

    private final SecureRandom random = new SecureRandom();

    String next() {
        StringBuilder code = new StringBuilder(LENGTH);
        for (int i = 0; i < LENGTH; i++) {
            code.append(BASE62.charAt(random.nextInt(BASE62.length())));
        }
        return code.toString();
    }
}
