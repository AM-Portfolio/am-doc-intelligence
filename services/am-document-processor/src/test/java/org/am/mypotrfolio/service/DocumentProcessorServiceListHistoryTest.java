package org.am.mypotrfolio.service;

import org.am.mypotrfolio.model.BatchProcessingStatus;
import org.am.mypotrfolio.model.BatchSyncHistoryResponse;
import org.am.mypotrfolio.model.BatchSyncRecord;
import org.am.mypotrfolio.model.FileSyncRecord;
import org.am.mypotrfolio.model.ProcessingStatus;
import org.am.mypotrfolio.repository.BatchSyncRecordRepository;
import org.am.mypotrfolio.service.detection.BrokerDetectionService;
import org.am.mypotrfolio.service.processor.DocumentProcessor;
import org.am.mypotrfolio.service.splitter.MultiPortfolioSplitterFactory;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.Executor;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class DocumentProcessorServiceListHistoryTest {

    @Mock
    private DocumentProcessor documentProcessor;
    @Mock
    private BrokerDetectionService brokerDetectionService;
    @Mock
    private MultiPortfolioSplitterFactory splitterFactory;
    @Mock
    private BatchSyncRecordRepository batchSyncRecordRepository;
    @Mock
    private BatchSyncEventPublisher eventPublisher;
    @Mock
    private Executor docProcessingPool;

    private DocumentProcessorService service;

    @BeforeEach
    void setUp() {
        service = new DocumentProcessorService(
                documentProcessor,
                brokerDetectionService,
                splitterFactory,
                batchSyncRecordRepository,
                eventPublisher,
                docProcessingPool);
    }

    @Test
    void listBatchSyncHistory_filtersByUserAndRespectsLimit() {
        BatchSyncRecord older = batch("user-a", BatchProcessingStatus.COMPLETED,
                LocalDateTime.now().minusDays(2));
        BatchSyncRecord newer = batch("user-a", BatchProcessingStatus.PARTIAL,
                LocalDateTime.now().minusHours(1));
        when(batchSyncRecordRepository.findByUserIdOrderByCreatedAtDesc("user-a"))
                .thenReturn(List.of(newer, older));

        BatchSyncHistoryResponse response = service.listBatchSyncHistory("user-a", 1, null);

        assertEquals(1, response.getItems().size());
        assertEquals(newer.getBatchId(), response.getItems().get(0).getBatchId().toString());
    }

    @Test
    void listBatchSyncHistory_filtersByOverallStatus() {
        BatchSyncRecord completed = batch("user-a", BatchProcessingStatus.COMPLETED,
                LocalDateTime.now().minusHours(2));
        BatchSyncRecord failed = batch("user-a", BatchProcessingStatus.FAILED,
                LocalDateTime.now().minusHours(1));
        when(batchSyncRecordRepository.findByUserIdOrderByCreatedAtDesc("user-a"))
                .thenReturn(List.of(failed, completed));

        BatchSyncHistoryResponse response =
                service.listBatchSyncHistory("user-a", 50, "completed");

        assertEquals(1, response.getItems().size());
        assertEquals(BatchProcessingStatus.COMPLETED, response.getItems().get(0).getOverallStatus());
    }

    @Test
    void listBatchSyncHistory_rejectsInvalidStatus() {
        IllegalArgumentException ex = assertThrows(
                IllegalArgumentException.class,
                () -> service.listBatchSyncHistory("user-a", 10, "not-a-status"));
        assertTrue(ex.getMessage().contains("Invalid status"));
    }

    private static BatchSyncRecord batch(
            String userId, BatchProcessingStatus overall, LocalDateTime createdAt) {
        return BatchSyncRecord.builder()
                .batchId(UUID.randomUUID().toString())
                .userId(userId)
                .overallStatus(overall)
                .createdAt(createdAt)
                .totalFiles(1)
                .files(List.of(FileSyncRecord.builder()
                        .fileId(UUID.randomUUID())
                        .fileName("holdings.xlsx")
                        .status(ProcessingStatus.COMPLETED)
                        .build()))
                .build();
    }
}
