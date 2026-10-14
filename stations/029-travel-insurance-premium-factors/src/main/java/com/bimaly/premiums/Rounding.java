package com.bimaly.premiums;

import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;

/** Two ways to round paise to whole rupees. Two beans of one type: @Primary is the default, @Qualifier picks the other. */
@FunctionalInterface
interface Rounding {

    long toRupee(long paise);

    @Configuration
    class Beans {

        /** The default: nearest rupee, for figures we only display. */
        @Bean
        @Primary
        Rounding nearestRupee() {
            return paise -> Math.round(paise / 100.0) * 100;
        }

        /** The insurer's rule for what is charged: always up to the next rupee, never down. */
        @Bean
        @Qualifier("premium")
        Rounding upToRupee() {
            return paise -> Math.ceilDiv(paise, 100) * 100;
        }
    }
}
