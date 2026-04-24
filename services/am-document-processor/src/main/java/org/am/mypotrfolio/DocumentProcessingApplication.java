package org.am.mypotrfolio;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.context.annotation.ComponentScans;
import org.springframework.data.mongodb.repository.config.EnableMongoRepositories;

import lombok.extern.slf4j.Slf4j;

@Slf4j
@SpringBootApplication
@ComponentScans({
    @ComponentScan("org.am.mypotrfolio"),
    @ComponentScan("com.am.common.amcommondata.service"),
    @ComponentScan("org.am.mypotrfolio.service.mapper"),
    @ComponentScan("com.am.common.amcommondata.mapper")
})
@EnableMongoRepositories(basePackages = "com.am.common.amcommondata.repository")
public class DocumentProcessingApplication {

    public static void main(String[] args) {
        ConfigurableApplicationContext context = SpringApplication.run(DocumentProcessingApplication.class, args);
        log.info("Document Processing Application Started");
    }
}
