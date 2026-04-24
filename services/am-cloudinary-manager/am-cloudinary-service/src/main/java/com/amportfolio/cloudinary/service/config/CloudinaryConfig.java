package com.amportfolio.cloudinary.service.config;

import com.cloudinary.Cloudinary;
import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.HashMap;
import java.util.Map;

/**
 * Configuration for Cloudinary integration
 */
@Configuration
@ConfigurationProperties(prefix = "cloudinary")
@Data
public class CloudinaryConfig {
    
    private String cloudName;
    private String apiKey;
    private String apiSecret;
    private boolean secure = true;
    
    /**
     * Default folder for uploads if not specified
     */
    private String defaultFolder = "uploads";
    
    /**
     * Creates and configures the Cloudinary bean
     * 
     * @return configured Cloudinary instance
     */
    @Bean
    public Cloudinary cloudinary() {
        Map<String, String> config = new HashMap<>();
        config.put("cloud_name", cloudName);
        config.put("api_key", apiKey);
        config.put("api_secret", apiSecret);
        config.put("secure", String.valueOf(secure));
        
        return new Cloudinary(config);
    }
}
