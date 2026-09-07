package org.am.mypotrfolio.service.detection;

import com.am.common.amcommondata.model.enums.BrokerType;
import lombok.extern.slf4j.Slf4j;
import org.am.mypotrfolio.domain.common.DocumentType;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.multipart.MultipartFile;

import java.util.Set;

/**
 * PDF-text-based broker detection using Apache PDFBox.
 *
 * <p>Extracts text from the first 2 pages of the PDF and scans for well-known
 * broker / document identifiers. Confidence is 90 — textual content is very
 * reliable unless the PDF is purely image-based (scanned), in which case
 * extraction yields an empty string and the strategy returns unknown.</p>
 *
 * <p>Signatures detected:</p>
 * <ul>
 *   <li>Zerodha — "Zerodha Broking", "ZERODHA SECURITIES"</li>
 *   <li>Groww — "Groww Invest Tech"</li>
 *   <li>Dhan — "Dhan HQ", "DHAN"</li>
 *   <li>Angel One — "Angel One Limited", "Angel Broking"</li>
 *   <li>CDSL CAS — "CDSL", "Consolidated Account Statement"</li>
 *   <li>NSDL CAS — "NSDL", "Consolidated Account Statement"</li>
 * </ul>
 */
@Slf4j
@Component
@Order(3)
public class PdfTextBrokerDetectionStrategy implements BrokerDetectionStrategy {

    private static final Set<String> PDF_EXTENSIONS = Set.of("pdf");
    private static final int PDF_CONFIDENCE = 90;
    private static final int MAX_PAGES_TO_SCAN = 2;

    @Override
    public boolean supports(String fileExtension) {
        return fileExtension != null && PDF_EXTENSIONS.contains(fileExtension.toLowerCase());
    }

    @Override
    public int confidence(MultipartFile file, String passwordHint) {
        if (file == null) return 0;
        try {
            return detect(file, passwordHint).isKnown() ? PDF_CONFIDENCE : 0;
        } catch (Exception e) {
            log.debug("PDF confidence check failed for {}: {}", file.getOriginalFilename(), e.getMessage());
            return 0;
        }
    }

    @Override
    public DetectionResult detect(MultipartFile file, String passwordHint) {
        try {
            byte[] bytes = file.getBytes();
            PDDocument document = passwordHint != null && !passwordHint.isBlank()
                    ? PDDocument.load(bytes, passwordHint)
                    : PDDocument.load(bytes);

            try (document) {
                PDFTextStripper stripper = new PDFTextStripper();
                stripper.setStartPage(1);
                stripper.setEndPage(Math.min(MAX_PAGES_TO_SCAN, document.getNumberOfPages()));
                String text = stripper.getText(document).toUpperCase();

                if (text.isBlank()) {
                    log.debug("PDF text extraction yielded empty content (possibly scanned image): {}", file.getOriginalFilename());
                    return DetectionResult.unknown();
                }

                return resolveFromText(text);
            }
        } catch (Exception e) {
            log.debug("PDF text detection failed for {}: {}", file.getOriginalFilename(), e.getMessage());
            return DetectionResult.unknown();
        }
    }

    private DetectionResult resolveFromText(String text) {
        // CAS documents — multiple portfolios inside one PDF
        if ((text.contains("CDSL") || text.contains("NSDL"))
                && text.contains("CONSOLIDATED ACCOUNT STATEMENT")) {
            return new DetectionResult(null, DocumentType.MUTUAL_FUND, PDF_CONFIDENCE);
        }
        if (text.contains("ZERODHA BROKING") || text.contains("ZERODHA SECURITIES")) {
            DocumentType dt = text.contains("CONTRACT NOTE") ? DocumentType.TRADE_EQ : DocumentType.STOCK_PORTFOLIO;
            return new DetectionResult(BrokerType.ZERODHA, dt, PDF_CONFIDENCE);
        }
        if (text.contains("GROWW INVEST TECH") || text.contains("GROWW SECURITIES")) {
            return new DetectionResult(BrokerType.GROWW, DocumentType.STOCK_PORTFOLIO, PDF_CONFIDENCE);
        }
        if (text.contains("DHAN HQ") || (text.contains("DHAN") && text.contains("HOLDINGS"))) {
            return new DetectionResult(BrokerType.DHAN, DocumentType.STOCK_PORTFOLIO, PDF_CONFIDENCE);
        }
        if (text.contains("ANGEL ONE LIMITED") || text.contains("ANGEL BROKING")) {
            return new DetectionResult(BrokerType.ANGEL_ONE, DocumentType.STOCK_PORTFOLIO, PDF_CONFIDENCE);
        }
        if (text.contains("UPSTOX") || text.contains("RKSV SECURITIES")) {
            return new DetectionResult(BrokerType.UPSTOX, DocumentType.STOCK_PORTFOLIO, PDF_CONFIDENCE);
        }
        return DetectionResult.unknown();
    }
}
