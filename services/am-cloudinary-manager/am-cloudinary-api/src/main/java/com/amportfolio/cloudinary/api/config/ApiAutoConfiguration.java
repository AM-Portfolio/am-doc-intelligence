package com.amportfolio.cloudinary.api.config;

import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.context.annotation.Import;

/**
 * Auto-configuration for API module
 */
import org.springframework.context.annotation.Bean;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@AutoConfiguration
@ConditionalOnProperty(prefix = "am.cloudinary.api", name = "enabled", havingValue = "true", matchIfMissing = true)
@ComponentScan(basePackages = "com.amportfolio.cloudinary.api")
@Import({OpenApiConfig.class})
public class ApiAutoConfiguration {
    
    /**
     * Configures CORS for the API to allow cross-origin requests from the frontend
     * @return WebMvcConfigurer with CORS configuration
     */
    @Bean
    public WebMvcConfigurer corsConfigurer() {
        return new WebMvcConfigurer() {
            @Override
            public void addCorsMappings(CorsRegistry registry) {
                registry.addMapping("/**")
                    .allowedOrigins("*") // Allow all origins
                    .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS")
                    .allowedHeaders("*")
                    .allowCredentials(false) // Must be false when allowing all origins
                    .maxAge(3600); // 1 hour max age
            }
        };
    }
}
