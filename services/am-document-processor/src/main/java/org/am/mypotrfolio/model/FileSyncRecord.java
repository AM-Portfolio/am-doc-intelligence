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
 * Per-file tracking record stored inside {@link BatchSyncRecord}.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class FileSyncRecord {

    private UUID fileId;
    private String fileName;

    /** Auto-detected or user-supplied broker. */
    private BrokerType detectedBroker;
    /** Auto-detected or user-supplied document type. */
    private String detectedDocumentType;

    private ProcessingStatus status;
    private String errorMessage;
    private int recordsProcessed;

    private LocalDateTime startedAt;
    private LocalDateTime completedAt;
}
