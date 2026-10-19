package com.hireloop.candidates;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Written first. The old system hashed passwords with a single MD5 pass. This shows why that is broken, and that
 * bcrypt fixes it: a leak of MD5 hashes is cracked instantly from a tiny list; bcrypt's hashes are not.
 */
class FastHashTrapTest extends ApiTest {

    @Autowired
    PasswordEncoder passwords;

    /** The 25 passwords an attacker tries first; the real breach lists run to millions, and MD5 clears them in seconds. */
    static final List<String> COMMON = List.of("123456", "password", "123456789", "12345678", "qwerty", "abc123", "football",
            "monkey", "letmein", "111111", "iloveyou", "admin", "welcome", "summer2024!", "login", "princess", "solo",
            "passw0rd", "starwars", "dragon", "master", "hello", "freedom", "whatever", "trustno1");

    private static String md5(String text) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("MD5").digest(text.getBytes()));
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
    }

    @Test
    void anMd5LeakIsCrackedFromACommonPasswordList() {
        String leaked = md5("summer2024!");   // Priya's password, as the old table stored it
        String cracked = COMMON.stream().filter(guess -> md5(guess).equals(leaked)).findFirst().orElseThrow();
        assertThat(cracked).isEqualTo("summer2024!");   // one pass of MD5 per guess: the whole list in well under a millisecond
    }

    @Test
    void theSameLeakOfBcryptHashesRevealsNothing() {
        String stored = passwords.encode("summer2024!");   // what the new system stores
        assertThat(stored).startsWith("{bcrypt}$2");
        assertThat(COMMON.stream().anyMatch(guess -> stored.contains(md5(guess)))).isFalse();   // the MD5 is nowhere in the bcrypt hash
        assertThat(passwords.matches("summer2024!", stored)).isTrue();   // only the real password verifies, and each check is deliberately slow
    }

    @Test
    void aLegacyMd5AccountIsUpgradedToBcryptOnFirstSignIn() throws Exception {
        assertThat(hashOf("priya@example.com")).startsWith("{MD5}");
        me("priya@example.com", "summer2024!").andExpect(org.springframework.test.web.servlet.result.MockMvcResultMatchers.status().isOk());
        assertThat(hashOf("priya@example.com")).startsWith("{bcrypt}$2");   // re-hashed the moment the right password was seen
        me("priya@example.com", "summer2024!").andExpect(org.springframework.test.web.servlet.result.MockMvcResultMatchers.status().isOk());   // still works after the upgrade
    }
}
