package com.kartwala.refunds;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.springframework.web.ErrorResponseException;

import java.time.Clock;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.Arrays;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * Challenge 1: Kartwala starts selling shoes. Add a FOOTWEAR category: 15 days, accepts every reason except
 * NOT_AS_DESCRIBED, and like clothing, a customer's-choice return needs the tags attached. Nothing else may change:
 * the station's own table must stay green.
 */
class FootwearChallengeTest {

    static final LocalDate TODAY = LocalDate.of(2026, 10, 15);

    @ParameterizedTest(name = "footwear delivered {0} days ago, {1}, tags {2} -> {3}")
    @CsvSource(textBlock = """
            15, SIZE_ISSUE,       true,  ''
            16, DAMAGED,          true,  WINDOW_CLOSED
            4,  CHANGED_MIND,     false, TAGS_REMOVED
            4,  WRONG_ITEM,       false, ''
            4,  NOT_AS_DESCRIBED, true,  REASON_NOT_ACCEPTED
            """)
    void footwearRules(int daysAgo, Reason reason, boolean tags, String refused) {
        Order shoes = new Order("KW-2001", "Running shoes", Category.valueOf("FOOTWEAR"), 299_900, TODAY.minusDays(daysAgo), false);
        List<String> expected = refused.isEmpty() ? List.of() : Arrays.asList(refused.split("\\|"));
        assertThat(RefundRules.check(shoes, reason, tags, null, TODAY).reasons()).containsExactlyElementsOf(expected);
    }

    @Test
    void theTagsQuestionIsRequiredForFootwear() {
        OrderLookup orders = mock(OrderLookup.class);
        when(orders.find("KW-2001")).thenReturn(Optional.of(
                new Order("KW-2001", "Running shoes", Category.valueOf("FOOTWEAR"), 299_900, TODAY, false)));
        RefundService service = new RefundService(orders, mock(EligibilityAudit.class), Clock.fixed(Instant.parse("2026-10-15T06:00:00Z"), ZoneOffset.UTC));
        assertThatThrownBy(() -> service.check("KW-2001", Reason.SIZE_ISSUE, null, null))
                .isInstanceOfSatisfying(ErrorResponseException.class, e -> assertThat(e.getBody().getDetail()).isEqualTo("tagsAttached is required for footwear."));
    }
}
