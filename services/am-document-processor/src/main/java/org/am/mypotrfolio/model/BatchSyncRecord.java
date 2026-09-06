package org.am.mypotrfolio.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * Durable MongoDB record for a multi-broker batch sync operation.
 *
 * <p>Replaces the volatile in-memory {@code ConcurrentHashMap<UUID, ProcessingStatus>}
 * that was in {@code DocumentProcessorService}. This record survives pod restarts and
 * is queryable for audit / support purposes.</p>
 *
 * <p>Collection: {@code batch_sync_records}</p>
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Document(collection = "batch_sync_records")
public class BatchSyncRecord {

    @Id
    private String batchId;

    @Indexed
    private String userId;

    /** Overall batch status — recomputed from file statuses on each update. */
    private BatchProcessingStatus overallStatus;

    @Builder.Default
    private List<FileSyncRecord> files = new ArrayList<>();

    private int totalFiles;

    @Builder.Default
    private LocalDateTime createdAt = LocalDateTime.now();

    private LocalDateTime updatedAt;

    // -------------------------------------------------------------------------
    // Convenience counters (computed on demand — not persisted separately)
    // -------------------------------------------------------------------------

    public long countByStatus(ProcessingStatus status) {
        return files.stream().filter(f -> f.getStatus() == status).count();
    }

    public int getCompleted() {
        return (int) countByStatus(ProcessingStatus.COMPLETED);
    }

    public int getFailed() {
        return (int) countByStatus(ProcessingStatus.FAILED);
    }

    /** Recomputes {@link #overallStatus} from child file statuses. */
    public void recomputeOverallStatus() {
        long total = files.size();
        long done = countByStatus(ProcessingStatus.COMPLETED);
        long failed = countByStatus(ProcessingStatus.FAILED);
        long active = countByStatus(ProcessingStatus.PROCESSING) + countByStatus(ProcessingStatus.QUEUED);

        if (active > 0) {
            overallStatus = BatchProcessingStatus.PROCESSING;
        } else if (failed == total) {
            overallStatus = BatchProcessingStatus.FAILED;
        } else if (done == total) {
            overallStatus = BatchProcessingStatus.COMPLETED;
        } else {
            overallStatus = BatchProcessingStatus.PARTIAL;
        }
        updatedAt = LocalDateTime.now();
    }
}
