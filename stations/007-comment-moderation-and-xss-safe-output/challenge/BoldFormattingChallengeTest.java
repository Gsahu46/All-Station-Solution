package com.chaupal.comments;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/** Challenge 1: **bold** becomes <strong>bold</strong> in the HTML, without opening a door for any other tag. */
class BoldFormattingChallengeTest extends ApiTest {

    private String shown(String text) throws Exception {
        comment("ravi", 1, text);
        return html(1).replaceAll("(?s).*<p>(.*)</p>.*", "$1");
    }

    @Test
    void doubleStarsBecomeStrong() throws Exception {
        assertThat(shown("**Amruttulya** is the best")).isEqualTo("<strong>Amruttulya</strong> is the best");
    }

    @Test
    void realTagsStayEncodedNextToTheFormatting() throws Exception {
        assertThat(shown("**yes** <b>no</b>")).isEqualTo("<strong>yes</strong> &lt;b&gt;no&lt;/b&gt;");
    }

    @Test
    void anAttackInsideTheStarsIsStillText() throws Exception {
        assertThat(shown("**<img src=x onerror=alert(1)>**")).isEqualTo("<strong>&lt;img src=x onerror=alert(1)&gt;</strong>");
    }

    @Test
    void unmatchedStarsStayAsTyped() throws Exception {
        assertThat(shown("5 ** 2 is not bold")).isEqualTo("5 ** 2 is not bold");
    }
}
