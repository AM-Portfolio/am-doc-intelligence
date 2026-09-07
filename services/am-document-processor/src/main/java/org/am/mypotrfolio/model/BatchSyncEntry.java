package org.am.mypotrfolio.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.web.multipart.MultipartFile;

/**
 * Represents a single file in a multi-broker batch sync request.
 * All fields except {@code file} are optional — broker, document type, and
 * password will be auto-detected when not provided.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class BatchSyncEntry {

    /** The uploaded file. Required. */
    private MultipartFile file;

    /**
     * Optional explicit broker type hint (e.g. "ZERODHA", "DHAN").
     * When provided it overrides auto-detection. Useful when the user knows
     * the broker but the filename/content detection might be ambiguous.
     */
    private String brokerType;

    /**
     * Optional explicit document type (e.g. "STOCK_PORTFOLIO", "MUTUAL_FUND").
     * When provided it overrides auto-detection.
     */
    private String documentType;

    /**
     * Optional password for encrypted files (e.g. Angel One password-protected Excel).
     * Per-file so each file in a batch can have a different password.
     */
    private String password;

    /**
     * Optional portfolio ID override for this specific file.
     * When null, falls back to the batch-level portfolioId.
     */
    private String portfolioId;
}
