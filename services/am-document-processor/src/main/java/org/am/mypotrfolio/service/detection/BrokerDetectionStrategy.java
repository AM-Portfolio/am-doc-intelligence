package org.am.mypotrfolio.service.detection;

import org.springframework.web.multipart.MultipartFile;

/**
 * Strategy interface for detecting the broker type from an uploaded file.
 *
 * <p>Multiple implementations are registered as Spring beans. {@link BrokerDetectionService}
 * collects all of them, runs each that {@link #supports} the given extension, and
 * picks the result with the highest {@link #confidence} score.</p>
 *
 * <p>Implementors must be stateless — they will be injected as singletons.</p>
 */
public interface BrokerDetectionStrategy {

    /**
     * Returns a confidence score in [0, 100].
     * Return 0 if this strategy cannot determine the broker for the given file.
     */
    int confidence(MultipartFile file, String passwordHint);

    /**
     * Performs the actual detection. Called only when {@link #confidence} > 0.
     */
    DetectionResult detect(MultipartFile file, String passwordHint);

    /**
     * Guards the strategy so it is only invoked for file extensions it understands.
     * Extension is lower-cased (e.g. "xlsx", "csv", "pdf").
     */
    boolean supports(String fileExtension);
}
