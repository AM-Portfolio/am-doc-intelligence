package org.am.mypotrfolio.model;

public enum ProcessingStatus {
    QUEUED,
    PROCESSING,
    COMPLETED,
    FAILED,
    /** Duplicate broker in the same batch — latest file kept, this one not processed. */
    SKIPPED
}
