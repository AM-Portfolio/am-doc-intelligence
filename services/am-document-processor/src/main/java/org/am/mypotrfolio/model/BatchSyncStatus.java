package org.am.mypotrfolio.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

/**
 * Overall status response for a batch sync operation.
 * Returned by {@code GET /v1/documents/sync/{batchId}/status}.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class BatchSyncStatus {

    private UUID batchId;
    private int total;
    private int completed;
    private int failed;
    private BatchProcessingStatus overallStatus;
    private List<FileSyncStatus> files;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
