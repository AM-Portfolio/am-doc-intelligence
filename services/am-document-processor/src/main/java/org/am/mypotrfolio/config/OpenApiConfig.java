package org.am.mypotrfolio.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.info.Info;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class OpenApiConfig {

    @Bean
    public OpenAPI openAPI() {
        return new OpenAPI()
                .info(new Info()
                        .title("Document Processor API")
                        .description("API for processing portfolio documents from various brokers")
                        .version("1.0.0")
                        .contact(new Contact()
                                .name("AM Portfolio Team")));
    }
}
