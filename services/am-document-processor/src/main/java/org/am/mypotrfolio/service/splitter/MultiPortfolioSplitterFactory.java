package org.am.mypotrfolio.service.splitter;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.am.mypotrfolio.domain.common.DocumentRequest;
import org.am.mypotrfolio.service.detection.DetectionResult;
import org.springframework.stereotype.Component;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.UUID;

/**
 * Selects the appropriate {@link MultiPortfolioSplitter} for a given file and returns
 * either the split sub-requests or a single-element list wrapping the original file
 * (when no splitting is needed).
 *
 * <p>The factory also handles the trivial case: if no splitter can handle the file,
 * it creates one plain {@link DocumentRequest} from the original file, so callers
 * always get back a {@code List<DocumentRequest>} and do not need to branch.</p>
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class MultiPortfolioSplitterFactory {

    private final List<MultiPortfolioSplitter> splitters;

    /**
     * Returns one or more {@link DocumentRequest}s derived from the uploaded file.
     *
     * @param file        the uploaded file
     * @param detection   broker/docType detection result
     * @param userId      caller's user ID
     * @param portfolioId optional portfolio-id override
     * @param password    optional file password
     */
    public List<DocumentRequest> splitOrWrap(MultipartFile file, DetectionResult detection,
                                             String userId, String portfolioId, String password) {
        MultiPortfolioSplitter splitter = splitters.stream()
                .filter(s -> s.canSplit(file, detection))
                .findFirst()
                .orElse(null);

        if (splitter != null) {
            log.info("Splitting '{}' using {}", file.getOriginalFilename(),
                    splitter.getClass().getSimpleName());
            return splitter.split(file, detection, userId, portfolioId, password);
        }

        // No splitting needed — wrap as a single request.
        log.debug("No splitter applicable for '{}', treating as single document", file.getOriginalFilename());
        DocumentRequest single = DocumentRequest.builder()
                .requestId(UUID.randomUUID())
                .file(file)
                .brokerType(detection.getBrokerType())
                .documentType(detection.getDocumentType())
                .userId(userId)
                .portfolioId(portfolioId)
                .password(password)
                .build();
        return List.of(single);
    }
}
