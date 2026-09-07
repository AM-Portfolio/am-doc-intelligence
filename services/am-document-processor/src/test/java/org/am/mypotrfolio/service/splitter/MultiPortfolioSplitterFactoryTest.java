package org.am.mypotrfolio.service.splitter;

import com.am.common.amcommondata.model.enums.BrokerType;
import org.am.mypotrfolio.domain.common.DocumentRequest;
import org.am.mypotrfolio.domain.common.DocumentType;
import org.am.mypotrfolio.service.detection.DetectionResult;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.jupiter.api.Assertions.*;

class MultiPortfolioSplitterFactoryTest {

    @Test
    void wrapsAsSingleRequestWhenNoSplitterMatches() {
        MultiPortfolioSplitter never = stubSplitter(false, List.of());
        MultiPortfolioSplitterFactory factory = new MultiPortfolioSplitterFactory(List.of(never));
        MockMultipartFile file = file("holdings.xlsx");
        DetectionResult detection = new DetectionResult(
                BrokerType.ZERODHA, DocumentType.STOCK_PORTFOLIO, 90);

        List<DocumentRequest> out = factory.splitOrWrap(file, detection, "user-1", "pf-1", null);

        assertEquals(1, out.size());
        DocumentRequest request = out.get(0);
        assertSame(file, request.getFile());
        assertEquals(BrokerType.ZERODHA, request.getBrokerType());
        assertEquals(DocumentType.STOCK_PORTFOLIO, request.getDocumentType());
        assertEquals("user-1", request.getUserId());
        assertEquals("pf-1", request.getPortfolioId());
        assertNotNull(request.getRequestId());
    }

    @Test
    void wrapsWhenSplitterListIsEmpty() {
        MultiPortfolioSplitterFactory factory = new MultiPortfolioSplitterFactory(List.of());
        MockMultipartFile file = file("cas.pdf");
        DetectionResult detection = new DetectionResult(null, DocumentType.MUTUAL_FUND, 90);

        List<DocumentRequest> out = factory.splitOrWrap(file, detection, "user-1", null, "secret");

        assertEquals(1, out.size());
        assertEquals(DocumentType.MUTUAL_FUND, out.get(0).getDocumentType());
        assertEquals("secret", out.get(0).getPassword());
        assertNull(out.get(0).getBrokerType());
    }

    @Test
    void usesFirstMatchingSplitterAndSkipsLaterOnes() {
        AtomicInteger laterCalls = new AtomicInteger();
        DocumentRequest splitRequest = DocumentRequest.builder()
                .requestId(UUID.randomUUID())
                .brokerType(BrokerType.ANGEL_ONE)
                .documentType(DocumentType.STOCK_PORTFOLIO)
                .userId("user-1")
                .build();
        MultiPortfolioSplitter matching = stubSplitter(true, List.of(splitRequest));
        MultiPortfolioSplitter later = new MultiPortfolioSplitter() {
            @Override
            public boolean canSplit(MultipartFile file, DetectionResult detection) {
                laterCalls.incrementAndGet();
                return true;
            }

            @Override
            public List<DocumentRequest> split(MultipartFile file, DetectionResult detection,
                                               String userId, String portfolioId, String password) {
                laterCalls.incrementAndGet();
                return List.of();
            }
        };
        MultiPortfolioSplitterFactory factory = new MultiPortfolioSplitterFactory(List.of(matching, later));
        DetectionResult detection = new DetectionResult(
                BrokerType.ANGEL_ONE, DocumentType.COMBINE_PORTFOLIO, 85);

        List<DocumentRequest> out = factory.splitOrWrap(file("angel.xlsx"), detection, "user-1", null, null);

        assertEquals(1, out.size());
        assertSame(splitRequest, out.get(0));
        assertEquals(0, laterCalls.get(), "factory must stop at the first matching splitter");
    }

    private static MultiPortfolioSplitter stubSplitter(boolean canSplit, List<DocumentRequest> splitResult) {
        return new MultiPortfolioSplitter() {
            @Override
            public boolean canSplit(MultipartFile file, DetectionResult detection) {
                return canSplit;
            }

            @Override
            public List<DocumentRequest> split(MultipartFile file, DetectionResult detection,
                                               String userId, String portfolioId, String password) {
                if (!canSplit) {
                    throw new AssertionError("split must not be called when canSplit is false");
                }
                return splitResult;
            }
        };
    }

    private static MockMultipartFile file(String name) {
        return new MockMultipartFile("file", name, "application/octet-stream", new byte[]{1, 2, 3});
    }
}
