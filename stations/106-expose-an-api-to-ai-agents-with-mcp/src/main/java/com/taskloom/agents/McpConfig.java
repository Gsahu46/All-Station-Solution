package com.taskloom.agents;

import io.modelcontextprotocol.common.McpTransportContext;
import io.modelcontextprotocol.json.jackson3.JacksonMcpJsonMapper;
import io.modelcontextprotocol.server.transport.DefaultServerTransportSecurityValidator;
import org.springframework.ai.mcp.server.common.autoconfigure.properties.McpServerStreamableHttpProperties;
import org.springframework.ai.mcp.server.webmvc.transport.WebMvcStreamableServerTransportProvider;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.core.context.SecurityContextHolder;
import tools.jackson.databind.json.JsonMapper;

import java.util.List;
import java.util.Map;

@Configuration
class McpConfig {

    static final String CALLER = "taskloom.caller";

    /**
     * Spring AI's Streamable HTTP transport, with two additions: each request carries its signed-in caller to the tools
     * (read on the request's own thread, after the security filters), and browsers from other sites are refused by Origin.
     */
    @Bean
    WebMvcStreamableServerTransportProvider webMvcStreamableServerTransportProvider(JsonMapper json, McpServerStreamableHttpProperties properties,
                                                                                    @Value("${taskloom.agents.allowed-origins}") List<String> origins) {
        return WebMvcStreamableServerTransportProvider.builder()
                .jsonMapper(new JacksonMcpJsonMapper(json))
                .mcpEndpoint(properties.getMcpEndpoint())
                .securityValidator(DefaultServerTransportSecurityValidator.builder().allowedOrigins(origins).build())
                .contextExtractor(request -> {
                    var auth = SecurityContextHolder.getContext().getAuthentication();
                    return auth != null && auth.getPrincipal() instanceof Callers.Caller caller
                            ? McpTransportContext.create(Map.of(CALLER, caller)) : McpTransportContext.EMPTY;
                })
                .build();
    }
}
