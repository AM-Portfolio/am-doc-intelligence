package org.am.mypotrfolio.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;

/**
 * Spring Security Configuration for Document Processor Service
 * 
 * Per coding instructions (Service Communication Flow):
 * - API Gateway validates user JWT and generates service JWT
 * - API Gateway passes service JWT to this service via Authorization header
 * - API Gateway passes user_id via X-User-ID header
 * - This service TRUSTS the API Gateway (no manual JWT validation needed)
 * - Public endpoints allow unauthenticated access (e.g., /types)
 * - Protected endpoints require Authorization header (service JWT from gateway)
 * - All requests must come through API Gateway (internal service, no direct
 * access)
 */
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

        @Value("${auth.jwt.secret}")
        private String jwtSecret;

        @Bean
        public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
                http
                                // Enable CORS
                                .cors(org.springframework.security.config.Customizer.withDefaults())

                                // Disable CSRF (stateless REST API with JWT)
                                .csrf(csrf -> csrf.disable())

                                // Stateless session management (no cookies, JWT-based)
                                .sessionManagement(session -> session
                                                .sessionCreationPolicy(SessionCreationPolicy.STATELESS))

                                // Configure authorization rules
                                .authorizeHttpRequests(auth -> auth
                                                // ✅ PUBLIC ENDPOINTS - No authentication required
                                                // Can be accessed by anyone (API Gateway forwards these)
                                                .requestMatchers(
                                                                "/v1/documents/types", // Get supported document
                                                                                           // types (public info)
                                                                "/actuator/health", // Docker health check
                                                                "/actuator/health/live", // Kubernetes liveness probe
                                                                "/actuator/health/ready", // Kubernetes readiness probe
                                                                "/swagger-ui/**", // Swagger API documentation
                                                                "/v3/api-docs/**", // OpenAPI specification
                                                                "/v3/api-docs.yaml" // OpenAPI YAML
                                                ).permitAll()

                                                // ✅ PROTECTED ENDPOINTS - Require service JWT from API Gateway
                                                // Per coding instructions: API Gateway handles user JWT validation
                                                // and generates service JWT before forwarding
                                                .requestMatchers(
                                                                "/v1/documents/process", // Process single document
                                                                "/v1/documents/batch-process", // Process multiple
                                                                                                   // documents
                                                                "/v1/documents/status/**" // Get processing status
                                                ).authenticated() // Spring Security checks Authorization header exists

                                                // ❌ Deny all other endpoints (fail secure)
                                                .anyRequest().denyAll())

                                // ✅ ZERO TRUST: Enforce JWT Validation
                                .oauth2ResourceServer(oauth2 -> oauth2
                                                .jwt(jwt -> jwt
                                                                .decoder(jwtDecoder())
                                                                .jwtAuthenticationConverter(
                                                                                new org.am.mypotrfolio.security.CustomJwtConverter())))

                                // Disable HTTP Basic authentication (not needed, using JWT)
                                .httpBasic(basic -> basic.disable())

                                // Disable form login (API Gateway handles authentication)
                                .formLogin(form -> form.disable());

                return http.build();
        }

        @Bean
        public JwtDecoder jwtDecoder() {
                SecretKey key = new SecretKeySpec(jwtSecret.getBytes(), "HmacSHA256");
                return NimbusJwtDecoder.withSecretKey(key).build();
        }

        @Bean
        public org.springframework.web.cors.CorsConfigurationSource corsConfigurationSource() {
                org.springframework.web.cors.CorsConfiguration configuration = new org.springframework.web.cors.CorsConfiguration();
                configuration.setAllowedOrigins(
                                java.util.Arrays.asList("http://localhost:3000", "http://localhost:9004", "https://am.asrax.in"));
                configuration.setAllowedMethods(java.util.Arrays.asList("GET", "POST", "PUT", "DELETE", "OPTIONS"));
                configuration.setAllowedHeaders(java.util.Arrays.asList("*"));
                configuration.setAllowCredentials(true);
                // Required for Chrome's Private Network Access security model
                configuration.addExposedHeader("Access-Control-Allow-Private-Network");
                org.springframework.web.cors.UrlBasedCorsConfigurationSource source = new org.springframework.web.cors.UrlBasedCorsConfigurationSource();
                source.registerCorsConfiguration("/**", configuration);
                return source;
        }
}