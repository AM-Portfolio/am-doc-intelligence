package com.amportfolio.cloudinary.app;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

/**
 * Main application class for the Cloudinary integration
 */
@SpringBootApplication
@ComponentScan(basePackages = {"com.amportfolio.cloudinary"})
public class CloudinaryApplication {

    public static void main(String[] args) {
        SpringApplication.run(CloudinaryApplication.class, args);
    }
}
