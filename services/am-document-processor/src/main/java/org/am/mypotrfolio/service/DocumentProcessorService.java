package org.am.mypotrfolio.service;

import com.am.common.amcommondata.model.enums.BrokerType;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.am.mypotrfolio.domain.common.DocumentRequest;
import org.am.mypotrfolio.domain.common.DocumentType;
import org.am.mypotrfolio.model.*;
import org.am.mypotrfolio.repository.BatchSyncRecordRepository;
import org.am.mypotrfolio.service.detection.BrokerDetectionService;
import org.am.mypotrfolio.service.detection.DetectionResult;
import org.am.mypotrfolio.service.processor.DocumentProcessor;
import org.am.mypotrfolio.service.splitter.MultiPortfolioSplitterFactory;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executor;
import java.util.stream.Collectors;

/**
 * Core document processing service.
 *
 * <p>Supports two modes:</p>
 * <ol>
 *   <li><b>Single-file sync</b> ({@link #processDocument}) — existing behaviour,
 *       no breaking change.</li>
 *   <li><b>Multi-broker batch async</b> ({@link #submitBatchSync}) — accepts N files
 *       from N brokers, auto-detects each, processes them in parallel on the
 *       {@code docProcessingPool}, and persists durable status to MongoDB.</li>
 * </ol>
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class DocumentProcessorService {

    private static final Logger logger = LoggerFactory.getLogger(DocumentProcessorService.class);

    private final DocumentProcessor documentProcessor;
    private final BrokerDetectionService brokerDetectionService;
    private final MultiPortfolioSplitterFactory splitterFactory;
    private final BatchSyncRecordRepository batchSyncRecordRepository;
    private final BatchSyncEventPublisher eventPublisher;

    @Qualifier("docProcessingPool")
    private final Executor docProcessingPool;

    /** Per-batch locks so parallel file workers cannot clobber sibling Mongo updates. */
    private final ConcurrentHashMap<String, Object> batchLocks = new ConcurrentHashMap<>();

    // =========================================================================
    // Single-file (existing API — backward-compatible, unchanged behaviour)
    // =========================================================================

    public DocumentProcessResponse processDocument(MultipartFile file, DocumentType documentType,
                                                   String portfolioId, String explicitBrokerTypeStr,
                                                   String userId, String password) {
        DocumentRequest documentRequest = buildSingleRequest(
                file, documentType, portfolioId, explicitBrokerTypeStr, userId, password);

        log.info("[ProcessId: {}] Starting document processing for type: {}",
                documentRequest.getRequestId(), documentType);

        try {
            DocumentProcessResponse response = documentProcessor.processDocument(
                    documentRequest, portfolioId, userId);
            response.setProcessId(documentRequest.getRequestId());
            response.setStatus(ProcessingStatus.COMPLETED);
            log.info("[ProcessId: {}] Successfully completed document processing",
                    documentRequest.getRequestId());
            return response;
        } catch (Exception e) {
            log.error("[ProcessId: {}] Failed to process document: {}",
                    documentRequest.getRequestId(), e.getMessage(), e);
            throw new RuntimeException("Failed to process document: " + e.getMessage(), e);
        }
    }

    // =========================================================================
    // Multi-broker batch sync (new)
    // =========================================================================

    /**
     * Accepts a list of {@link BatchSyncEntry}s, persists a {@link BatchSyncRecord} to
     * MongoDB, and submits each entry to the {@code docProcessingPool} for parallel
     * async processing. Returns the initial {@link BatchSyncStatus} immediately — the
     * caller can poll {@code GET /sync/{batchId}/status} or stream via SSE.
     *
     * @param entries     one entry per file in the batch
     * @param userId      authenticated user
     * @param portfolioId optional batch-level portfolio-id override (per-entry value wins)
     */
    public BatchSyncStatus submitBatchSync(List<BatchSyncEntry> entries, String userId, String portfolioId) {
        UUID batchId = UUID.randomUUID();
        log.info("[BatchId: {}] Submitting batch sync of {} files for user: {}", batchId, entries.size(), userId);

        // Eagerly copy file bytes in the request thread — MultipartFile streams are
        // closed after the HTTP request completes, so async threads cannot read them.
        List<BatchSyncEntry> safEntries = new ArrayList<>();
        for (BatchSyncEntry entry : entries) {
            if (entry.getFile() != null) {
                try {
                    byte[] bytes = entry.getFile().getBytes();
                    String originalName = entry.getFile().getOriginalFilename();
                    String contentType = entry.getFile().getContentType();
                    MultipartFile safeFile = new ByteBackedMultipartFile(originalName, contentType, bytes);
                    safEntries.add(BatchSyncEntry.builder()
                            .file(safeFile)
                            .brokerType(entry.getBrokerType())
                            .documentType(entry.getDocumentType())
                            .password(entry.getPassword())
                            .portfolioId(entry.getPortfolioId())
                            .build());
                } catch (Exception e) {
                    log.error("[BatchId: {}] Failed to read file bytes for: {}", batchId,
                            entry.getFile().getOriginalFilename(), e);
                    throw new IllegalArgumentException(
                            "Could not read file: " + entry.getFile().getOriginalFilename());
                }
            } else {
                safEntries.add(entry);
            }
        }

        // Initialise per-file records as QUEUED
        List<FileSyncRecord> fileRecords = safEntries.stream().map(entry -> FileSyncRecord.builder()
                .fileId(UUID.randomUUID())
                .fileName(entry.getFile() != null ? entry.getFile().getOriginalFilename() : "unknown")
                .status(ProcessingStatus.QUEUED)
                .build()).collect(Collectors.toList());

        BatchSyncRecord batchRecord = BatchSyncRecord.builder()
                .batchId(batchId.toString())
                .userId(userId)
                .overallStatus(BatchProcessingStatus.QUEUED)
                .files(fileRecords)
                .totalFiles(safEntries.size())
                .createdAt(LocalDateTime.now())
                .build();
        batchSyncRecordRepository.save(batchRecord);

        // Submit each entry asynchronously
        for (int i = 0; i < safEntries.size(); i++) {
            final BatchSyncEntry entry = safEntries.get(i);
            final UUID fileId = fileRecords.get(i).getFileId();

            CompletableFuture.runAsync(
                    () -> processEntry(batchId, fileId, entry, userId, portfolioId),
                    docProcessingPool
            ).exceptionally(ex -> {
                log.error("[BatchId: {}][FileId: {}] Unhandled exception in async processor", batchId, fileId, ex);
                updateFileStatus(batchId, fileId, ProcessingStatus.FAILED, ex.getMessage(), null, 0);
                return null;
            });
        }

        return toBatchSyncStatus(batchRecord);
    }

    /**
     * Returns the latest {@link BatchSyncStatus} for the given batch and user.
     *
     * @throws IllegalArgumentException if not found or not owned by the user
     */
    public BatchSyncStatus getBatchSyncStatus(String batchId, String userId) {
        BatchSyncRecord record = batchSyncRecordRepository
                .findByBatchIdAndUserId(batchId, userId)
                .orElseThrow(() -> new IllegalArgumentException("Batch not found: " + batchId));
        return toBatchSyncStatus(record);
    }

    // =========================================================================
    // Legacy batch endpoint (kept for backward compatibility — @Deprecated)
    // =========================================================================

    /**
     * @deprecated Use {@link #submitBatchSync(List, String, String)} instead.
     *             This method forces one brokerType for all files and runs sequentially.
     */
    @Deprecated(since = "multi-broker-sync", forRemoval = true)
    public List<DocumentProcessResponse> processBatchDocuments(List<MultipartFile> files,
                                                               DocumentType documentType,
                                                               String portfolioId,
                                                               String explicitBrokerTypeStr,
                                                               String userId) {
        UUID batchId = UUID.randomUUID();
        log.info("[BatchId: {}] (deprecated) Starting sequential batch processing of {} documents",
                batchId, files.size());
        List<DocumentProcessResponse> responses = new ArrayList<>();
        for (MultipartFile file : files) {
            responses.add(processDocument(file, documentType, portfolioId, null, userId, null));
        }
        return responses;
    }

    public List<String> getSupportedDocumentTypes() {
        return List.of(
                "COMBINE_PORTFOLIO", "MUTUAL_FUND", "NPS_STATEMENT",
                "COMPANY_FINANCIAL_REPORT", "STOCK_PORTFOLIO", "TRADE_FNO", "TRADE_EQ",
                "TRADE_MF", "NSE_INDICES");
    }

    public ProcessingStatus getProcessingStatus(UUID processId) {
        // Legacy in-memory status is no longer maintained; return completed for any stored record
        return ProcessingStatus.COMPLETED;
    }

    // =========================================================================
    // Private helpers
    // =========================================================================

    /** Core async worker: detect → split → process each sub-request → persist + emit. */
    private void processEntry(UUID batchId, UUID fileId, BatchSyncEntry entry,
                              String userId, String batchPortfolioId) {
        String fileName = entry.getFile() != null ? entry.getFile().getOriginalFilename() : "unknown";
        log.info("[BatchId: {}][FileId: {}] Starting processing for file: {}", batchId, fileId, fileName);

        try {
            // 1. Detect broker & document type
            BrokerType explicitBroker = parseBrokerType(entry.getBrokerType());
            DocumentType explicitDocType = parseDocumentType(entry.getDocumentType());
            DetectionResult detection = brokerDetectionService.detectWithHints(
                    entry.getFile(), entry.getPassword(), explicitBroker, explicitDocType);

            updateFileDetection(batchId, fileId, detection, ProcessingStatus.PROCESSING);
            log.info("[BatchId: {}][FileId: {}] Detected broker={} docType={} confidence={}",
                    batchId, fileId, detection.getBrokerType(), detection.getDocumentType(),
                    detection.getConfidence());

            // Guard: if detection failed and no hints were provided, fail early with a clear message
            if (detection.getBrokerType() == null && detection.getDocumentType() == null) {
                throw new IllegalArgumentException(
                        "Could not detect broker or document type for file: " + fileName +
                        ". Please provide 'brokerTypes' and/or 'documentTypes' hints in the request.");
            }

            // 2. Split multi-portfolio files if needed
            String effectivePortfolioId = entry.getPortfolioId() != null
                    ? entry.getPortfolioId() : batchPortfolioId;
            List<DocumentRequest> requests = splitterFactory.splitOrWrap(
                    entry.getFile(), detection, userId, effectivePortfolioId, entry.getPassword());

            log.info("[BatchId: {}][FileId: {}] Split into {} sub-requests", batchId, fileId, requests.size());

            // 3. Process each sub-request (synchronous within this async worker)
            int totalRecords = 0;
            for (DocumentRequest req : requests) {
                DocumentProcessResponse resp = documentProcessor.processDocument(
                        req, req.getPortfolioId(), userId);
                totalRecords += resp.getTotalRecords();
            }

            updateFileStatus(batchId, fileId, ProcessingStatus.COMPLETED, null, detection, totalRecords);
            log.info("[BatchId: {}][FileId: {}] Completed with {} records", batchId, fileId, totalRecords);

        } catch (Exception e) {
            log.error("[BatchId: {}][FileId: {}] Failed to process file: {}", batchId, fileId, fileName, e);
            updateFileStatus(batchId, fileId, ProcessingStatus.FAILED, e.getMessage(), null, 0);
        }
    }

    private void updateFileDetection(UUID batchId, UUID fileId, DetectionResult detection,
                                     ProcessingStatus status) {
        withBatchLock(batchId, () -> {
            BatchSyncRecord record = batchSyncRecordRepository.findById(batchId.toString()).orElse(null);
            if (record == null) return;

            record.getFiles().stream()
                    .filter(f -> fileId.equals(f.getFileId()))
                    .findFirst()
                    .ifPresent(f -> {
                        f.setDetectedBroker(detection.getBrokerType());
                        f.setDetectedDocumentType(detection.getDocumentType() != null
                                ? detection.getDocumentType().name() : null);
                        f.setStatus(status);
                        f.setStartedAt(LocalDateTime.now());
                    });

            record.recomputeOverallStatus();
            batchSyncRecordRepository.save(record);

            FileSyncStatus sse = buildFileSyncStatus(record.getFiles().stream()
                    .filter(f -> fileId.equals(f.getFileId())).findFirst().orElse(null));
            if (sse != null) {
                eventPublisher.emit(batchId, sse);
            }
        });
    }

    private void updateFileStatus(UUID batchId, UUID fileId, ProcessingStatus status,
                                  String errorMessage, DetectionResult detection, int records) {
        withBatchLock(batchId, () -> {
            BatchSyncRecord record = batchSyncRecordRepository.findById(batchId.toString()).orElse(null);
            if (record == null) {
                log.warn("[BatchId: {}] Record not found during status update", batchId);
                return;
            }

            record.getFiles().stream()
                    .filter(f -> fileId.equals(f.getFileId()))
                    .findFirst()
                    .ifPresent(f -> {
                        f.setStatus(status);
                        f.setErrorMessage(errorMessage);
                        f.setRecordsProcessed(records);
                        f.setCompletedAt(LocalDateTime.now());
                        if (detection != null && f.getDetectedBroker() == null) {
                            f.setDetectedBroker(detection.getBrokerType());
                            f.setDetectedDocumentType(detection.getDocumentType() != null
                                    ? detection.getDocumentType().name() : null);
                        }
                    });

            record.recomputeOverallStatus();
            batchSyncRecordRepository.save(record);

            FileSyncStatus sse = buildFileSyncStatus(record.getFiles().stream()
                    .filter(f -> fileId.equals(f.getFileId())).findFirst().orElse(null));
            if (sse != null) {
                eventPublisher.emit(batchId, sse);
            }

            if (record.getOverallStatus() == BatchProcessingStatus.COMPLETED
                    || record.getOverallStatus() == BatchProcessingStatus.FAILED
                    || record.getOverallStatus() == BatchProcessingStatus.PARTIAL) {
                eventPublisher.completeBatch(batchId);
                batchLocks.remove(batchId.toString());
            }
        });
    }

    private void withBatchLock(UUID batchId, Runnable action) {
        Object lock = batchLocks.computeIfAbsent(batchId.toString(), k -> new Object());
        synchronized (lock) {
            action.run();
        }
    }

    private DocumentRequest buildSingleRequest(MultipartFile file, DocumentType documentType,
                                               String portfolioId, String explicitBrokerTypeStr,
                                               String userId, String password) {
        UUID processId = UUID.randomUUID();
        BrokerType explicitBroker = parseBrokerType(explicitBrokerTypeStr);
        DetectionResult detection = brokerDetectionService.detectWithHints(
                file, password, explicitBroker, documentType);
        String rawBrokerType = "UPSTOX".equalsIgnoreCase(explicitBrokerTypeStr) ? "UPSTOX" : null;

        return DocumentRequest.builder()
                .requestId(processId)
                .file(file)
                .documentType(detection.getDocumentType() != null ? detection.getDocumentType() : documentType)
                .brokerType(detection.getBrokerType())
                .rawBrokerType(rawBrokerType)
                .portfolioId(portfolioId)
                .userId(userId)
                .password(password)
                .build();
    }

    private BatchSyncStatus toBatchSyncStatus(BatchSyncRecord record) {
        List<FileSyncStatus> fileStatuses = record.getFiles().stream()
                .map(this::buildFileSyncStatus)
                .collect(Collectors.toList());

        return BatchSyncStatus.builder()
                .batchId(UUID.fromString(record.getBatchId()))
                .total(record.getTotalFiles())
                .completed(record.getCompleted())
                .failed(record.getFailed())
                .overallStatus(record.getOverallStatus())
                .files(fileStatuses)
                .createdAt(record.getCreatedAt())
                .updatedAt(record.getUpdatedAt())
                .build();
    }

    private FileSyncStatus buildFileSyncStatus(FileSyncRecord f) {
        if (f == null) return null;
        return FileSyncStatus.builder()
                .fileId(f.getFileId())
                .fileName(f.getFileName())
                .detectedBroker(f.getDetectedBroker())
                .detectedDocumentType(f.getDetectedDocumentType())
                .status(f.getStatus())
                .errorMessage(f.getErrorMessage())
                .recordsProcessed(f.getRecordsProcessed())
                .startedAt(f.getStartedAt())
                .completedAt(f.getCompletedAt())
                .build();
    }

    private BrokerType parseBrokerType(String str) {
        if (str == null || str.isBlank()) return null;
        try { return BrokerType.valueOf(str.toUpperCase()); }
        catch (IllegalArgumentException e) { return null; }
    }

    private DocumentType parseDocumentType(String str) {
        if (str == null || str.isBlank()) return null;
        try { return DocumentType.valueOf(str.toUpperCase()); }
        catch (IllegalArgumentException e) { return null; }
    }

    /**
     * A simple byte-backed {@link MultipartFile} that can be safely passed to async threads.
     * Unlike Tomcat's {@code StandardMultipartFile}, this keeps file contents in memory so
     * the input stream is always available regardless of HTTP request lifecycle.
     */
    private static class ByteBackedMultipartFile implements org.springframework.web.multipart.MultipartFile {
        private final String name;
        private final String originalFilename;
        private final String contentType;
        private final byte[] bytes;

        ByteBackedMultipartFile(String originalFilename, String contentType, byte[] bytes) {
            this.name = "file";
            this.originalFilename = originalFilename;
            this.contentType = contentType;
            this.bytes = bytes;
        }

        @Override public String getName() { return name; }
        @Override public String getOriginalFilename() { return originalFilename; }
        @Override public String getContentType() { return contentType; }
        @Override public boolean isEmpty() { return bytes == null || bytes.length == 0; }
        @Override public long getSize() { return bytes == null ? 0 : bytes.length; }
        @Override public byte[] getBytes() { return bytes; }
        @Override public java.io.InputStream getInputStream() { return new java.io.ByteArrayInputStream(bytes); }
        @Override public void transferTo(java.io.File dest) throws java.io.IOException {
            try (java.io.FileOutputStream fos = new java.io.FileOutputStream(dest)) {
                fos.write(bytes);
            }
        }
    }
}
