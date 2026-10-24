package com.bimaly.policies;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.oxm.jaxb.Jaxb2Marshaller;
import org.springframework.ws.client.core.WebServiceTemplate;
import org.springframework.ws.client.support.interceptor.ClientInterceptor;
import org.springframework.ws.transport.http.JdkHttpClientMessageSender;

import java.net.http.HttpClient;
import java.time.Duration;

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

    /** The SOAP client, with both timeouts: a stuck insurer costs a request at most `timeout`. */
    @Bean
    WebServiceTemplate insurer(Jaxb2Marshaller messages, @Value("${bimaly.insurer.url}") String url,
                               @Value("${bimaly.insurer.connect-timeout}") Duration connectTimeout,
                               @Value("${bimaly.insurer.timeout}") Duration timeout) {
        // Given its HttpClient: made by hand inside a @Bean method, the sender never builds its own (that is done in
        // afterPropertiesSet, which only runs for beans) and fails with "HttpClient is not available".
        JdkHttpClientMessageSender sender = new JdkHttpClientMessageSender(HttpClient.newBuilder().connectTimeout(connectTimeout).build());
        sender.setRequestTimeout(timeout);
        WebServiceTemplate template = new WebServiceTemplate(messages);
        template.setDefaultUri(url);
        template.setMessageSender(sender);
        template.setInterceptors(new ClientInterceptor[]{new SoapLog()});   // challenge 1
        return template;
    }
}
