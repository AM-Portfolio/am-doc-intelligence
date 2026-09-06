package org.am.mypotrfolio.model;

/**
 * Overall status of a multi-file batch sync operation.
 */
public enum BatchProcessingStatus {
    /** Batch has been accepted but no file has started processing yet. */
    QUEUED,
    /** At least one file is being actively processed. */
    PROCESSING,
    /** All files finished — some may have failed. */
    COMPLETED,
    /** All files failed. */
    FAILED,
    /** Some files succeeded, some failed. */
    PARTIAL
}
