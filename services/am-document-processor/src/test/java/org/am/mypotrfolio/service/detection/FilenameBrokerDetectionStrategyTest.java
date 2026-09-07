package org.am.mypotrfolio.service.detection;

import com.am.common.amcommondata.model.enums.BrokerType;
import org.am.mypotrfolio.domain.common.DocumentType;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockMultipartFile;

import static org.junit.jupiter.api.Assertions.*;

class FilenameBrokerDetectionStrategyTest {

    private final FilenameBrokerDetectionStrategy strategy = new FilenameBrokerDetectionStrategy();

    @Test
    void detectsZerodhaFromFilename() {
        DetectionResult result = strategy.detect(file("zerodha_holdings.xlsx"), null);
        assertEquals(BrokerType.ZERODHA, result.getBrokerType());
        assertEquals(DocumentType.STOCK_PORTFOLIO, result.getDocumentType());
        assertTrue(result.isKnown());
    }

    @Test
    void detectsGrowwHoldingsStatementWithoutBrokerWord() {
        DetectionResult result = strategy.detect(
                file("Stocks_Holdings_Statement_3060484652_2026-01-21.xlsx"), null);
        assertEquals(BrokerType.GROWW, result.getBrokerType());
        assertEquals(DocumentType.STOCK_PORTFOLIO, result.getDocumentType());
    }

    @Test
    void doesNotTreatGenericHoldingsPrefixAsUpstox() {
        DetectionResult result = strategy.detect(file("Holdings_Statement_2026-05-24.xlsx"), null);
        assertNotEquals(BrokerType.UPSTOX, result.getBrokerType());
        assertEquals(BrokerType.GROWW, result.getBrokerType());
    }

    @Test
    void detectsUpstoxWhenNameContainsBroker() {
        DetectionResult result = strategy.detect(file("upstox_holdings.xlsx"), null);
        assertEquals(BrokerType.UPSTOX, result.getBrokerType());
    }

    @Test
    void unknownWhenFilenameHasNoBrokerHint() {
        DetectionResult result = strategy.detect(file("random_export.csv"), null);
        assertFalse(result.isKnown());
        assertEquals(0, strategy.confidence(file("random_export.csv"), null));
    }

    private static MockMultipartFile file(String name) {
        return new MockMultipartFile("file", name, "application/octet-stream", new byte[]{1, 2, 3});
    }
}
