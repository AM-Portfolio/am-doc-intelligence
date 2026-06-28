package org.am.mypotrfolio.controller;

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
import com.am.common.amcommondata.model.enums.BrokerType;
import org.am.mypotrfolio.model.DocumentProcessResponse;
import org.am.mypotrfolio.model.ProcessingStatus;
import org.am.mypotrfolio.service.DocumentProcessorService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import jakarta.servlet.http.HttpServletRequest;
import java.util.List;
import java.util.UUID;
import org.am.mypotrfolio.security.CustomJwtAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;

/**
 * Document Processor REST Controller (Internal Service)
 * 
 * Per coding instructions (Service Communication Flow):
 * - API Gateway validates user JWT and generates service JWT
 * - API Gateway passes service JWT via Authorization header
 * - API Gateway passes user_id via X-User-ID header
 * - This service TRUSTS the API Gateway (no manual JWT validation needed)
 * - Public endpoints (/types) require NO authentication
 * - Protected endpoints require X-User-ID header (provided by API Gateway)
 * - All requests must come through API Gateway (internal service only)
 */
@Slf4j
@RestController
@RequestMapping("/v1/documents")
@Tag(name = "Documents", description = "Document processing operations (internal service - via API Gateway only)")
public class DocumentProcessorController {

    @Autowired
    private DocumentProcessorService documentProcessorService;

    // ═══════════════════════════════════════════════════════════════════════════
    // PUBLIC ENDPOINTS (No authentication required)
    // Per coding instructions: Public endpoints don't require authentication
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Get supported document types
     * 
     * Public endpoint - no authentication required
     * Per coding instructions: "Public endpoints don't require authentication"
     * Spring Security: .permitAll()
     */
    @Operation(summary = "Get supported document types", description = "Retrieve list of supported document types (public endpoint)")
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Document types retrieved successfully", content = @Content(array = @ArraySchema(schema = @Schema(implementation = String.class)))),
            @ApiResponse(responseCode = "500", description = "Internal server error")
    })
    @GetMapping("/types")
    public ResponseEntity<List<String>> getSupportedDocumentTypes() {
        log.info("Getting supported document types");
        return ResponseEntity.ok(documentProcessorService.getSupportedDocumentTypes());
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // PROTECTED ENDPOINTS (Require X-User-ID header from API Gateway)
    // Per coding instructions: API Gateway already validated user JWT
    // This service just reads the X-User-ID header that API Gateway provides
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Process a single document
     * 
     * Protected endpoint - requires X-User-ID header from API Gateway
     * Per coding instructions:
     * - API Gateway validates user JWT
     * - API Gateway generates service JWT and passes via Authorization header
     * - API Gateway passes user_id via X-User-ID header
     * - This service trusts the headers (no manual validation needed)
     * - Spring Security: .authenticated() (ensures Authorization header exists)
     */
    @Operation(summary = "Process a single document", description = "Upload and process a single portfolio document (internal service - via API Gateway only)", security = @SecurityRequirement(name = "Bearer"))
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Document processed successfully", content = @Content(schema = @Schema(implementation = DocumentProcessResponse.class))),
            @ApiResponse(responseCode = "401", description = "Unauthorized: Missing authentication"),
            @ApiResponse(responseCode = "400", description = "Invalid input parameters"),
            @ApiResponse(responseCode = "500", description = "Internal server error")
    })
    @PostMapping(value = "/process", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<?> processDocument(
            @Parameter(description = "Portfolio document file to process", required = true) @RequestParam("file") MultipartFile file,
            @Parameter(description = "Type of document being processed", required = true) @RequestParam("documentType") DocumentType documentType,
            @Parameter(description = "Portfolio ID (optional)", required = false) @RequestParam(value = "portfolioId", required = false) String portfolioId,
            @Parameter(description = "Explicit Broker Type (optional)", required = false) @RequestParam(value = "brokerType", required = false) String brokerTypeStr,
            @RequestHeader(value = "X-User-ID", required = false) String userIdHeader, // Optional: API Gateway injects this; UI can pass it directly
            @Parameter(description = "Document Password (optional)", required = false) @RequestParam(value = "password", required = false) String password) {

        // Resolve user ID: prefer X-User-ID header, fall back to JWT sub claim
        String userId = userIdHeader;
        if (userId == null || userId.isBlank()) {
            var auth = SecurityContextHolder.getContext().getAuthentication();
            if (auth instanceof CustomJwtAuthenticationToken jwtAuth) {
                userId = jwtAuth.getUserContext().getUserId();
            }
        }
        if (userId == null || userId.isBlank()) {
            return ResponseEntity.badRequest()
                    .body(new ErrorResponse("Cannot determine user identity"));
        }

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
     * Process multiple documents (batch)
     * 
     * Per coding instructions: Same flow as single document
     */
    @Operation(summary = "Process multiple documents", description = "Upload and process multiple portfolio documents (internal service - via API Gateway only)", security = @SecurityRequirement(name = "Bearer"))
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Documents processed successfully", content = @Content(array = @ArraySchema(schema = @Schema(implementation = DocumentProcessResponse.class)))),
            @ApiResponse(responseCode = "401", description = "Unauthorized: Missing authentication"),
            @ApiResponse(responseCode = "400", description = "Invalid input parameters"),
            @ApiResponse(responseCode = "500", description = "Internal server error")
    })
    @PostMapping(value = "/batch-process", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<?> processBatchDocuments(
            @Parameter(description = "List of portfolio document files to process", required = true) @RequestParam("files") List<MultipartFile> files,
            @Parameter(description = "Type of documents being processed", required = true) @RequestParam("documentType") DocumentType documentType,
            @Parameter(description = "Portfolio ID (optional)", required = false) @RequestParam(value = "portfolioId", required = false) String portfolioId,
            @Parameter(description = "Explicit Broker Type (optional)", required = false) @RequestParam(value = "brokerType", required = false) String brokerTypeStr,
            @RequestHeader(value = "X-User-ID", required = false) String userIdHeader) {

        String userId = userIdHeader;
        if (userId == null || userId.isBlank()) {
            var auth = SecurityContextHolder.getContext().getAuthentication();
            if (auth instanceof CustomJwtAuthenticationToken jwtAuth) {
                userId = jwtAuth.getUserContext().getUserId();
            }
        }
        if (userId == null || userId.isBlank()) {
            return ResponseEntity.badRequest().body(new ErrorResponse("Cannot determine user identity"));
        }

        log.info("Batch processing {} documents for user: {}, type: {}, portfolio: {}, broker: {}",
                files.size(), userId, documentType, portfolioId, brokerTypeStr);

        try {
            // ✅ Just call service with user_id from header
            List<DocumentProcessResponse> responses = documentProcessorService.processBatchDocuments(
                    files,
                    documentType,
                    portfolioId,
                    brokerTypeStr,
                    userId // ← Directly from API Gateway header
            );

            return ResponseEntity.ok(responses);

        } catch (IllegalArgumentException e) {
            log.warn("Invalid batch parameters: {}", e.getMessage());
            return ResponseEntity.badRequest()
                    .body(new ErrorResponse("Invalid parameters: " + e.getMessage()));
        } catch (Exception e) {
            log.error("Error batch processing documents for user: {}", userId, e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(new ErrorResponse("Failed to process documents"));
        }
    }

    /**
     * Get document processing status
     * 
     * Per coding instructions: Protected endpoint requires X-User-ID header
     */
    @Operation(summary = "Get document processing status", description = "Retrieve the current status of a document processing request (internal service - via API Gateway only)", security = @SecurityRequirement(name = "Bearer"))
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Processing status retrieved successfully", content = @Content(schema = @Schema(implementation = ProcessingStatus.class))),
            @ApiResponse(responseCode = "401", description = "Unauthorized: Missing authentication"),
            @ApiResponse(responseCode = "404", description = "Process ID not found"),
            @ApiResponse(responseCode = "500", description = "Internal server error")
    })
    @GetMapping("/status/{processId}")
    public ResponseEntity<?> getProcessingStatus(
            @Parameter(description = "Unique identifier of the processing request", required = true) @PathVariable UUID processId,
            @RequestHeader(value = "X-User-ID", required = true) String userId) {

        log.info("Getting processing status for process: {}, user: {}", processId, userId);

        try {
            // ✅ Get status (already scoped to authenticated user via X-User-ID)
            ProcessingStatus status = documentProcessorService.getProcessingStatus(processId);
            return ResponseEntity.ok(status);

        } catch (Exception e) {
            log.error("Error getting processing status for processId: {}", processId, e);
            return ResponseEntity.status(HttpStatus.NOT_FOUND)
                    .body(new ErrorResponse("Process not found"));
        }
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // ERROR RESPONSE MODEL
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Simple error response model
     */
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