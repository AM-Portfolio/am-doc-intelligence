package org.am.mypotrfolio.service.splitter;

import org.am.mypotrfolio.domain.common.DocumentRequest;
import org.am.mypotrfolio.service.detection.DetectionResult;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

/**
 * Strategy for splitting a single uploaded file that contains data for multiple
 * portfolios or brokers into individual {@link DocumentRequest}s — one per
 * logical portfolio segment.
 *
 * <p>Examples of files that need splitting:</p>
 * <ul>
 *   <li>CDSL/NSDL CAS PDF — multiple folios across many fund houses in one PDF.</li>
 *   <li>Angel One COMBINE_PORTFOLIO Excel — Equity sheet + Mutual Fund sheet.</li>
 *   <li>User-created aggregated Excel with one sheet per broker.</li>
 * </ul>
 */
public interface MultiPortfolioSplitter {

    /**
     * Returns {@code true} if this splitter can handle the given file/detection combination.
     */
    boolean canSplit(MultipartFile file, DetectionResult detection);

    /**
     * Splits the file into a list of {@link DocumentRequest}s, one per logical portfolio segment.
     * Each returned request is a self-contained unit that can be processed independently.
     *
     * @param file        the original uploaded file
     * @param detection   auto-detection result (may carry broker + docType hints)
     * @param userId      caller's user ID
     * @param portfolioId optional portfolio-id override (may be null)
     * @param password    optional file password (may be null)
     */
    List<DocumentRequest> split(MultipartFile file, DetectionResult detection,
                                String userId, String portfolioId, String password);
}
