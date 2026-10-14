package com.paysetu.payments;

import com.fasterxml.jackson.annotation.JsonSubTypes;
import org.junit.jupiter.api.Test;

import java.lang.reflect.RecordComponent;
import java.util.Arrays;
import java.util.Set;
import java.util.stream.Collectors;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Every permitted payment method, found by reflection, so a method added later is covered without editing this test:
 * it can be sent as JSON, and it has a next action and a refund route.
 */
class EveryMethodTest {

    @Test
    void paymentMethodIsSealed() {
        assertThat(PaymentMethod.class.isSealed()).isTrue();
    }

    @Test
    void everyMethodCanArriveAsJson() {
        Set<Class<?>> registered = Arrays.stream(PaymentMethod.class.getAnnotation(JsonSubTypes.class).value())
                .map(JsonSubTypes.Type::value).collect(Collectors.toSet());
        assertThat(registered).containsExactlyInAnyOrder(PaymentMethod.class.getPermittedSubclasses());
    }

    @Test
    void everyMethodHasANextActionAndARefundRoute() throws Exception {
        for (Class<?> type : PaymentMethod.class.getPermittedSubclasses()) {
            PaymentMethod method = sample(type);
            assertThat(Methods.nextAction(method, "Rs 1.00").detail()).as(type.getSimpleName()).isNotBlank();
            assertThat(Methods.refundRoute(method)).as(type.getSimpleName()).isNotBlank();
        }
    }

    /** A record with placeholder values: "9876543210" for text, the first constant of an enum, 1 for numbers. */
    static PaymentMethod sample(Class<?> type) throws Exception {
        RecordComponent[] components = type.getRecordComponents();
        Object[] args = Arrays.stream(components).map(c -> {
            Class<?> t = c.getType();
            if (t.isEnum()) return t.getEnumConstants()[0];
            if (t == String.class) return "9876543210";
            if (t == long.class || t == Long.class) return 1L;
            return 1;
        }).toArray();
        return (PaymentMethod) type.getDeclaredConstructor(Arrays.stream(components).map(RecordComponent::getType).toArray(Class[]::new))
                .newInstance(args);
    }
}
