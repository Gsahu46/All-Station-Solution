package com.dakroute.rates;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.servers.Server;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

import java.util.List;

@SpringBootApplication
public class RatesApplication {

    public static void main(String[] args) {
        SpringApplication.run(RatesApplication.class, args);
    }

    /** The parts of the docs that are not in the code: title, version, where partners send requests. */
    @Bean
    OpenAPI partnerDocs() {
        return new OpenAPI()
                .info(new Info().title("Dakroute shipping rates").version("3.0")
                        .description("Prices for parcels between Indian PIN codes, for partners. Demo tariff.")
                        .contact(new Contact().name("Dakroute partner support").email("partners@dakroute.example")))
                .servers(List.of(new Server().url("https://api.dakroute.example").description("Partner API (example address)")));
    }
}
