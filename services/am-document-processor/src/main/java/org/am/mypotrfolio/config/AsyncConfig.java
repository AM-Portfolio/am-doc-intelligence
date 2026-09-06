package org.am.mypotrfolio.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

import java.util.concurrent.Executor;

/**
 * Async configuration for the document processing pipeline.
 *
 * <p>A dedicated thread pool ({@code docProcessingPool}) is used for batch
 * document processing so that parallel uploads do not starve the servlet
 * container threads. Pool sizes are externally configurable via application
 * properties.</p>
 *
 * <pre>
 * doc.processing.pool.size     — core pool size (default 5)
 * doc.processing.pool.max      — max pool size  (default 10)
 * doc.processing.pool.queue    — queue capacity  (default 100)
 * </pre>
 */
@Configuration
@EnableAsync
public class AsyncConfig {

    @Bean("docProcessingPool")
    public Executor docProcessingPool(
            @Value("${doc.processing.pool.size:5}") int coreSize,
            @Value("${doc.processing.pool.max:10}") int maxSize,
            @Value("${doc.processing.pool.queue:100}") int queueCapacity) {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(coreSize);
        executor.setMaxPoolSize(maxSize);
        executor.setQueueCapacity(queueCapacity);
        executor.setThreadNamePrefix("doc-proc-");
        executor.setWaitForTasksToCompleteOnShutdown(true);
        executor.setAwaitTerminationSeconds(60);
        executor.initialize();
        return executor;
    }
}
