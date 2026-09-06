package org.am.mypotrfolio.controller;

import com.am.security.context.UserContext;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.ArraySchema;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.extern.slf4j.Slf4j;
import org.am.mypotrfolio.domain.common.DocumentType;
import org.am.mypotrfolio.model.*;
import org.am.mypotrfolio.service.BatchSyncEventPublisher;
import org.am.mypotrfolio.service.DocumentProcessorService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * Document Processor REST Controller.
 *
 * Auth is enforced by {@code am-security-lib} (OIDC JWKS). Controllers read
 * user identity from {@link UserContext} — same pattern as am-analysis /
 * am-cloudinary-manager.
 */
@Slf4j
@RestController
@RequestMapping("/v1/documents")
@Tag(name = "Documents", description = "Document processing operations")
public class DocumentProcessorController {

    @Autowired
    private DocumentProcessorService documentProcessorService;

    @Autowired
    private BatchSyncEventPublisher batchSyncEventPublisher;

    @Operation(summary = "Get supported document types", description = "Public endpoint — no authentication required")
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Document types retrieved successfully", content = @Content(array = @ArraySchema(schema = @Schema(implementation = String.class)))),
            @ApiResponse(responseCode = "500", description = "Internal server error")
    })
    @GetMapping("/types")
    public ResponseEntity<List<String>> getSupportedDocumentTypes() {
        log.info("Getting supported document types");
        return ResponseEntity.ok(documentProcessorService.getSupportedDocumentTypes());
    }

    @Operation(summary = "Process a single document", security = @SecurityRequirement(name = "Bearer"))
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Document processed successfully", content = @Content(schema = @Schema(implementation = DocumentProcessResponse.class))),
            @ApiResponse(responseCode = "401", description = "Unauthorized"),
            @ApiResponse(responseCode = "400", description = "Invalid input parameters"),
            @ApiResponse(responseCode = "500", description = "Internal server error")
    })
    @PostMapping(value = "/process", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<?> processDocument(
            @Parameter(description = "Portfolio document file to process", required = true) @RequestParam("file") MultipartFile file,
            @Parameter(description = "Type of document being processed", required = true) @RequestParam("documentType") DocumentType documentType,
            @Parameter(description = "Portfolio ID (optional)", required = false) @RequestParam(value = "portfolioId", required = false) String portfolioId,
            @Parameter(description = "Explicit Broker Type (optional)", required = false) @RequestParam(value = "brokerType", required = false) String brokerTypeStr,
            @Parameter(description = "Document Password (optional)", required = false) @RequestParam(value = "password", required = false) String password) {

        String userId = resolveUserId();

        log.info("Processing document for user: {}, type: {}, portfolio: {}, broker: {}",
                userId, documentType, portfolioId, brokerTypeStr);

        try {
            DocumentProcessResponse response = documentProcessorService.processDocument(
                    file,
                    documentType,
                    portfolioId,
                    brokerTypeStr,
                    userId,
                    password
            );
            return ResponseEntity.ok(response);
        } catch (IllegalArgumentException e) {
            log.warn("Invalid document parameters: {}", e.getMessage());
            return ResponseEntity.badRequest()
                    .body(new ErrorResponse("Invalid parameters: " + e.getMessage()));
        } catch (Exception e) {
            log.error("Error processing document for user: {}", userId, e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(new ErrorResponse("Failed to process document"));
        }
    }

    /**
     * @deprecated Use {@code POST /v1/documents/sync} instead. This endpoint forces a single
     *             brokerType for all files and processes them sequentially.
     */
    @Deprecated
    @Operation(summary = "[Deprecated] Process multiple documents with one shared broker type",
               description = "Deprecated — use POST /v1/documents/sync for multi-broker parallel processing.",
               security = @SecurityRequirement(name = "Bearer"))
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Documents processed successfully"),
            @ApiResponse(responseCode = "401", description = "Unauthorized"),
            @ApiResponse(responseCode = "400", description = "Invalid input parameters"),
            @ApiResponse(responseCode = "500", description = "Internal server error")
    })
    @PostMapping(value = "/batch-process", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<?> processBatchDocuments(
            @Parameter(description = "List of portfolio document files to process", required = true)
            @RequestParam("files") List<MultipartFile> files,
            @Parameter(description = "Type of documents being processed", required = true)
            @RequestParam("documentType") DocumentType documentType,
            @Parameter(description = "Portfolio ID (optional)", required = false)
            @RequestParam(value = "portfolioId", required = false) String portfolioId,
            @Parameter(description = "Explicit Broker Type (optional)", required = false)
            @RequestParam(value = "brokerType", required = false) String brokerTypeStr) {

        String userId = resolveUserId();
        log.warn("Deprecated /batch-process called by user: {} — recommend migrating to /sync", userId);

        try {
            List<DocumentProcessResponse> responses = documentProcessorService.processBatchDocuments(
                    files, documentType, portfolioId, brokerTypeStr, userId);
            return ResponseEntity.ok(responses);
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(new ErrorResponse("Invalid parameters: " + e.getMessage()));
        } catch (Exception e) {
            log.error("Error in deprecated batch processing for user: {}", userId, e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(new ErrorResponse("Failed to process documents"));
        }
    }

    // =========================================================================
    // Multi-broker sync endpoints (new)
    // =========================================================================

    @Operation(
        summary = "Submit a multi-broker batch sync",
        description = "Accepts N files from N different brokers. Broker type and document type are " +
                      "auto-detected per file. Processing is parallel and non-blocking — the response " +
                      "is returned immediately with a batchId. Poll GET /sync/{batchId}/status or " +
                      "stream progress via GET /sync/{batchId}/stream.",
        security = @SecurityRequirement(name = "Bearer"))
    @ApiResponses({
            @ApiResponse(responseCode = "202", description = "Batch accepted and processing started",
                    content = @Content(schema = @Schema(implementation = BatchSyncStatus.class))),
            @ApiResponse(responseCode = "401", description = "Unauthorized"),
            @ApiResponse(responseCode = "400", description = "No valid files provided"),
            @ApiResponse(responseCode = "500", description = "Internal server error")
    })
    @PostMapping(value = "/sync", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<?> submitBatchSync(
            @Parameter(description = "Files to process (one or more, different brokers allowed)", required = true)
            @RequestParam("files") List<MultipartFile> files,
            @Parameter(description = "Optional per-file broker hints (same order as files, may be sparse)")
            @RequestParam(value = "brokerTypes", required = false) List<String> brokerTypes,
            @Parameter(description = "Optional per-file document type hints (same order as files)")
            @RequestParam(value = "documentTypes", required = false) List<String> documentTypes,
            @Parameter(description = "Optional per-file passwords for encrypted files")
            @RequestParam(value = "passwords", required = false) List<String> passwords,
            @Parameter(description = "Optional batch-level portfolio ID")
            @RequestParam(value = "portfolioId", required = false) String portfolioId) {

        String userId = resolveUserId();

        if (files == null || files.isEmpty()) {
            return ResponseEntity.badRequest().body(new ErrorResponse("At least one file is required"));
        }
        if (files.size() > 5) {
            return ResponseEntity.badRequest().body(new ErrorResponse("Maximum 5 files allowed per batch"));
        }

        log.info("Multi-broker sync request: {} files, user: {}", files.size(), userId);

        List<BatchSyncEntry> entries = new ArrayList<>();
        for (int i = 0; i < files.size(); i++) {
            entries.add(BatchSyncEntry.builder()
                    .file(files.get(i))
                    .brokerType(getOrNull(brokerTypes, i))
                    .documentType(getOrNull(documentTypes, i))
                    .password(getOrNull(passwords, i))
                    .build());
        }

        try {
            BatchSyncStatus status = documentProcessorService.submitBatchSync(entries, userId, portfolioId);
            return ResponseEntity.accepted().body(status);
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(new ErrorResponse(e.getMessage()));
        } catch (Exception e) {
            log.error("Error submitting batch sync for user: {}", userId, e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(new ErrorResponse("Failed to submit batch sync"));
        }
    }

    @Operation(
        summary = "Get batch sync status",
        description = "Returns the current status of a multi-broker batch sync, including per-file results.",
        security = @SecurityRequirement(name = "Bearer"))
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Status retrieved",
                    content = @Content(schema = @Schema(implementation = BatchSyncStatus.class))),
            @ApiResponse(responseCode = "401", description = "Unauthorized"),
            @ApiResponse(responseCode = "404", description = "Batch not found")
    })
    @GetMapping("/sync/{batchId}/status")
    public ResponseEntity<?> getBatchSyncStatus(
            @Parameter(description = "Batch ID returned by POST /sync", required = true)
            @PathVariable String batchId) {

        String userId = resolveUserId();
        try {
            BatchSyncStatus status = documentProcessorService.getBatchSyncStatus(batchId, userId);
            return ResponseEntity.ok(status);
        } catch (IllegalArgumentException e) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND)
                    .body(new ErrorResponse("Batch not found: " + batchId));
        } catch (Exception e) {
            log.error("Error retrieving batch status for batchId: {}", batchId, e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(new ErrorResponse("Failed to retrieve batch status"));
        }
    }

    @Operation(
        summary = "Stream batch sync progress via SSE",
        description = "Opens a Server-Sent Events stream that pushes a \"file-update\" event each time " +
                      "a file in the batch completes or fails, and a terminal \"batch-complete\" event " +
                      "when all files are done. The stream closes automatically when the batch finishes.",
        security = @SecurityRequirement(name = "Bearer"))
    @GetMapping(value = "/sync/{batchId}/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter streamBatchSyncProgress(
            @Parameter(description = "Batch ID returned by POST /sync", required = true)
            @PathVariable String batchId) {

        String userId = resolveUserId();
        log.info("SSE stream requested for batchId: {} by user: {}", batchId, userId);
        return batchSyncEventPublisher.subscribe(UUID.fromString(batchId));
    }

    private static <T> T getOrNull(List<T> list, int index) {
        return (list != null && index < list.size()) ? list.get(index) : null;
    }

    @Operation(summary = "Get document processing status", security = @SecurityRequirement(name = "Bearer"))
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Processing status retrieved successfully", content = @Content(schema = @Schema(implementation = ProcessingStatus.class))),
            @ApiResponse(responseCode = "401", description = "Unauthorized"),
            @ApiResponse(responseCode = "404", description = "Process ID not found"),
            @ApiResponse(responseCode = "500", description = "Internal server error")
    })
    @GetMapping("/status/{processId}")
    public ResponseEntity<?> getProcessingStatus(
            @Parameter(description = "Unique identifier of the processing request", required = true) @PathVariable UUID processId) {

        String userId = resolveUserId();
        log.info("Getting processing status for process: {}, user: {}", processId, userId);

        try {
            ProcessingStatus status = documentProcessorService.getProcessingStatus(processId);
            return ResponseEntity.ok(status);
        } catch (Exception e) {
            log.error("Error getting processing status for processId: {}", processId, e);
            return ResponseEntity.status(HttpStatus.NOT_FOUND)
                    .body(new ErrorResponse("Process not found"));
        }
    }

    /**
     * Prefer am-security-lib {@link UserContext} (set by UserContextFilter).
     * Fall back to OIDC {@link JwtAuthenticationToken} subject when the filter
     * has not populated the ThreadLocal yet.
     */
    private static String resolveUserId() {
        String userId = UserContext.getUserId();
        if (userId != null && !userId.isBlank()) {
            return userId;
        }
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth instanceof JwtAuthenticationToken jwtAuth) {
            String sub = jwtAuth.getToken().getSubject();
            if (sub != null && !sub.isBlank()) {
                return sub;
            }
        }
        log.warn("No authenticated user found. Falling back to local-dev-user");
        return "local-dev-user";
    }

    public static class ErrorResponse {
        public String error;
        public long timestamp;

        public ErrorResponse(String error) {
            this.error = error;
            this.timestamp = System.currentTimeMillis();
        }

        public String getError() {
            return error;
        }

        public long getTimestamp() {
            return timestamp;
        }
    }
}
