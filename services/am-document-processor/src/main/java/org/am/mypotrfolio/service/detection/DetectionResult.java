package org.am.mypotrfolio.service.detection;

import com.am.common.amcommondata.model.enums.BrokerType;
import lombok.Value;
import org.am.mypotrfolio.domain.common.DocumentType;

/**
 * Result produced by {@link BrokerDetectionService}.
 * Carries the detected broker, the inferred document type, and a confidence
 * score (0–100) so callers can decide whether to accept auto-detection or fall
 * back to a user-supplied hint.
 */
@Value
public class DetectionResult {

    BrokerType brokerType;
    DocumentType documentType;
    /** 0 = unknown, 100 = certain */
    int confidence;

    public static DetectionResult unknown() {
        return new DetectionResult(null, null, 0);
    }

    public boolean isKnown() {
        return brokerType != null && confidence > 0;
    }
}
