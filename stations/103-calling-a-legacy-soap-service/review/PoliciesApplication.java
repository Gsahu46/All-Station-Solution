package com.bimaly.policies;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.oxm.jaxb.Jaxb2Marshaller;
import org.springframework.ws.client.core.WebServiceTemplate;


@SpringBootApplication
public class PoliciesApplication {

    public static void main(String[] args) {
        SpringApplication.run(PoliciesApplication.class, args);
    }

    /** XML to and from the classes generated from the insurer's WSDL at build time. */
    @Bean
    Jaxb2Marshaller insurerMessages() {
        Jaxb2Marshaller marshaller = new Jaxb2Marshaller();
        marshaller.setContextPath("com.bimaly.policies.insurer");
        return marshaller;
    }

    /** The SOAP client. Spring-WS's defaults are fine for a partner we trust. */
    @Bean
    WebServiceTemplate insurer(Jaxb2Marshaller messages, @Value("${bimaly.insurer.url}") String url) {
        WebServiceTemplate template = new WebServiceTemplate(messages);
        template.setDefaultUri(url);
        return template;
    }
}
