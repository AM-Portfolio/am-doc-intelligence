package org.am.mypotrfolio.service.detection;

import com.am.common.amcommondata.model.enums.BrokerType;
import lombok.extern.slf4j.Slf4j;
import org.am.mypotrfolio.domain.common.DocumentType;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.multipart.MultipartFile;

import java.util.Set;

/**
 * Lowest-cost strategy: inspects the original filename for well-known broker keywords.
 * Confidence is moderate (60) — filename-based detection can be wrong if the user
 * renames the file, but it is always cheap and fast.
 *
 * <p>Supports all file extensions — filename is always available regardless of format.</p>
 */
@Slf4j
@Component
@Order(10)
public class FilenameBrokerDetectionStrategy implements BrokerDetectionStrategy {

    private static final Set<String> ALL_EXTENSIONS = Set.of("xlsx", "xls", "csv", "pdf");
    private static final int FILENAME_CONFIDENCE = 60;

    @Override
    public boolean supports(String fileExtension) {
        return fileExtension != null && ALL_EXTENSIONS.contains(fileExtension.toLowerCase());
    }

    @Override
    public int confidence(MultipartFile file, String passwordHint) {
        if (file == null || file.getOriginalFilename() == null) {
            return 0;
        }
        return resolveFromFilename(file.getOriginalFilename().toUpperCase()) != null
                ? FILENAME_CONFIDENCE : 0;
    }

    @Override
    public DetectionResult detect(MultipartFile file, String passwordHint) {
        String filename = file.getOriginalFilename();
        if (filename == null) {
            return DetectionResult.unknown();
        }
        String upper = filename.toUpperCase();
        BrokerType broker = resolveFromFilename(upper);
        if (broker == null) {
            return DetectionResult.unknown();
        }
        DocumentType docType = inferDocumentType(upper, broker);
        log.debug("Filename-based detection: file={} broker={} docType={}", filename, broker, docType);
        return new DetectionResult(broker, docType, FILENAME_CONFIDENCE);
    }

    private BrokerType resolveFromFilename(String upper) {
        if (upper.contains("DHAN")) return BrokerType.DHAN;
        if (upper.contains("ZERODHA")) return BrokerType.ZERODHA;
        if (upper.contains("MSTOCK")) return BrokerType.MSTOCK;
        if (upper.contains("GROWW") || upper.contains("STOCKS_HOLDINGS_STATEMENT")
                || upper.contains("MUTUAL_FUNDS_ORDER") || upper.contains("HOLDINGS_STATEMENT")) {
            return BrokerType.GROWW;
        }
        if (upper.contains("ANGEL") || upper.contains("ANGELONE")) return BrokerType.ANGEL_ONE;
        if (upper.contains("UPSTOX")) return BrokerType.UPSTOX;
        return null;
    }

    private DocumentType inferDocumentType(String upper, BrokerType broker) {
        if (upper.contains("TRADE") && upper.contains("FNO")) return DocumentType.TRADE_FNO;
        if (upper.contains("TRADE")) return DocumentType.TRADE_EQ;
        if (upper.contains("MF") || upper.contains("MUTUAL")) return DocumentType.MUTUAL_FUND;
        if (broker == BrokerType.ANGEL_ONE) return DocumentType.COMBINE_PORTFOLIO;
        return DocumentType.STOCK_PORTFOLIO;
    }
}
