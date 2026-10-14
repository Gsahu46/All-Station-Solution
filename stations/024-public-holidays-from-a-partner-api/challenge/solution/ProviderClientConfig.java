package com.teamdesk.holidays;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.support.RestClientAdapter;
import org.springframework.web.service.invoker.HttpServiceProxyFactory;

import java.net.http.HttpClient;
import java.time.Duration;

/**
 * Builds the provider client with time limits. Without them a slow provider holds our request thread for as long
 * as it likes, and enough slow calls take our whole API down with it.
 */
@Configuration
class ProviderClientConfig {

    @Bean
    HolidayProviderClient holidayProviderClient(@Value("${teamdesk.holidays.base-url}") String baseUrl,
                                                @Value("${teamdesk.holidays.connect-timeout}") Duration connectTimeout,
                                                @Value("${teamdesk.holidays.read-timeout}") Duration readTimeout,
                                                @Value("${teamdesk.holidays.api-key:}") String apiKey) {
        JdkClientHttpRequestFactory requests = new JdkClientHttpRequestFactory(
                HttpClient.newBuilder().connectTimeout(connectTimeout).build());
        requests.setReadTimeout(readTimeout);
        // Challenge 2: the key from configuration (an environment variable in real life), on every call, never logged.
        RestClient rest = RestClient.builder().baseUrl(baseUrl).requestFactory(requests).defaultHeader("X-Api-Key", apiKey).build();
        return HttpServiceProxyFactory.builderFor(RestClientAdapter.create(rest)).build().createClient(HolidayProviderClient.class);
    }
}
