package org.am.mypotrfolio.service.detection;

import com.am.common.amcommondata.model.enums.BrokerType;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.am.mypotrfolio.domain.common.DocumentType;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.util.Comparator;
import java.util.List;
import java.util.Objects;

/**
 * Orchestrates all registered {@link BrokerDetectionStrategy} beans.
 *
 * <p>Algorithm:</p>
 * <ol>
 *   <li>Filter strategies that {@link BrokerDetectionStrategy#supports support} the file's extension.</li>
 *   <li>Ask each supported strategy for its {@link BrokerDetectionStrategy#confidence confidence} score.</li>
 *   <li>Pick the strategy with the highest score (ties broken by {@link org.springframework.core.annotation.Order}).</li>
 *   <li>Invoke {@link BrokerDetectionStrategy#detect detect} on the winner.</li>
 *   <li>If a user-supplied explicit broker type is provided, it overrides the detected one but the detected
 *       {@link DocumentType} is preserved if the caller did not provide one.</li>
 * </ol>
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class BrokerDetectionService {

    private final List<BrokerDetectionStrategy> strategies;

    /**
     * Auto-detect broker and document type from the uploaded file.
     *
     * @param file         the uploaded file
     * @param passwordHint optional password for encrypted files
     * @return a {@link DetectionResult} — never null; use {@link DetectionResult#isKnown()} to check success
     */
    public DetectionResult detect(MultipartFile file, String passwordHint) {
        if (file == null || file.getOriginalFilename() == null) {
            return DetectionResult.unknown();
        }

        String ext = extractExtension(file.getOriginalFilename());
        log.debug("Running broker detection for file={} ext={}", file.getOriginalFilename(), ext);

        BrokerDetectionStrategy winner = strategies.stream()
                .filter(s -> s.supports(ext))
                .max(Comparator.comparingInt(s -> s.confidence(file, passwordHint)))
                .orElse(null);

        if (winner == null) {
            log.warn("No detection strategy supports extension '{}' for file: {}", ext, file.getOriginalFilename());
            return DetectionResult.unknown();
        }

        int score = winner.confidence(file, passwordHint);
        if (score == 0) {
            log.warn("All strategies returned 0 confidence for file: {}", file.getOriginalFilename());
            return DetectionResult.unknown();
        }

        DetectionResult result = winner.detect(file, passwordHint);
        log.info("Detected broker={} docType={} confidence={} strategy={} file={}",
                result.getBrokerType(), result.getDocumentType(), result.getConfidence(),
                winner.getClass().getSimpleName(), file.getOriginalFilename());
        return result;
    }

    /**
     * Merges auto-detection with optional user-supplied hints.
     * User-supplied values always win; detected values fill in the blanks.
     *
     * @param file              the uploaded file
     * @param passwordHint      optional password
     * @param explicitBroker    user-supplied broker (may be null)
     * @param explicitDocType   user-supplied doc type (may be null)
     */
    public DetectionResult detectWithHints(MultipartFile file, String passwordHint,
                                           BrokerType explicitBroker, DocumentType explicitDocType) {
        DetectionResult detected = detect(file, passwordHint);

        BrokerType broker = explicitBroker != null ? explicitBroker : detected.getBrokerType();
        DocumentType docType = explicitDocType != null ? explicitDocType : detected.getDocumentType();
        int confidence = explicitBroker != null ? 100 : detected.getConfidence();

        return new DetectionResult(broker, docType, confidence);
    }

    private String extractExtension(String filename) {
        int dot = filename.lastIndexOf('.');
        return dot >= 0 ? filename.substring(dot + 1).toLowerCase() : "";
    }
}
