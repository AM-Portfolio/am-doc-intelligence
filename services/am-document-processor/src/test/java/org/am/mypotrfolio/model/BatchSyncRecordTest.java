package org.am.mypotrfolio.model;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;

class BatchSyncRecordTest {

    @Test
    void recomputeOverallStatus_allQueuedStaysProcessingOnceAnyActive() {
        BatchSyncRecord record = record(
                ProcessingStatus.QUEUED,
                ProcessingStatus.PROCESSING);
        record.recomputeOverallStatus();
        assertEquals(BatchProcessingStatus.PROCESSING, record.getOverallStatus());
    }

    @Test
    void recomputeOverallStatus_allCompleted() {
        BatchSyncRecord record = record(
                ProcessingStatus.COMPLETED,
                ProcessingStatus.COMPLETED);
        record.recomputeOverallStatus();
        assertEquals(BatchProcessingStatus.COMPLETED, record.getOverallStatus());
        assertEquals(2, record.getCompleted());
        assertEquals(0, record.getFailed());
    }

    @Test
    void recomputeOverallStatus_allFailed() {
        BatchSyncRecord record = record(
                ProcessingStatus.FAILED,
                ProcessingStatus.FAILED);
        record.recomputeOverallStatus();
        assertEquals(BatchProcessingStatus.FAILED, record.getOverallStatus());
    }

    @Test
    void recomputeOverallStatus_mixedIsPartial() {
        BatchSyncRecord record = record(
                ProcessingStatus.COMPLETED,
                ProcessingStatus.FAILED);
        record.recomputeOverallStatus();
        assertEquals(BatchProcessingStatus.PARTIAL, record.getOverallStatus());
        assertEquals(1, record.getCompleted());
        assertEquals(1, record.getFailed());
    }

    private static BatchSyncRecord record(ProcessingStatus... statuses) {
        List<FileSyncRecord> files = new ArrayList<>();
        for (ProcessingStatus status : statuses) {
            files.add(FileSyncRecord.builder()
                    .fileId(UUID.randomUUID())
                    .fileName("f.xlsx")
                    .status(status)
                    .build());
        }
        return BatchSyncRecord.builder()
                .batchId(UUID.randomUUID().toString())
                .userId("user-1")
                .files(files)
                .totalFiles(files.size())
                .build();
    }
}
