package org.am.mypotrfolio.model;

import com.am.common.amcommondata.model.enums.BrokerType;
import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.UUID;

/**
 * Per-file status DTO returned in {@link BatchSyncStatus#getFiles()}.
 * This is the API-facing projection of {@link FileSyncRecord}.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class FileSyncStatus {

    private UUID fileId;
    private String fileName;
    private BrokerType detectedBroker;
    private String detectedDocumentType;
    private ProcessingStatus status;
    private String errorMessage;
    private int recordsProcessed;
    private LocalDateTime startedAt;
    private LocalDateTime completedAt;

    public boolean isTerminal() {
        return status == ProcessingStatus.COMPLETED || status == ProcessingStatus.FAILED;
    }
}
