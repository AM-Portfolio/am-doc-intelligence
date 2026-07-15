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
import org.am.mypotrfolio.model.DocumentProcessResponse;
import org.am.mypotrfolio.model.ProcessingStatus;
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

    @Operation(summary = "Process multiple documents", security = @SecurityRequirement(name = "Bearer"))
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Documents processed successfully", content = @Content(array = @ArraySchema(schema = @Schema(implementation = DocumentProcessResponse.class)))),
            @ApiResponse(responseCode = "401", description = "Unauthorized"),
            @ApiResponse(responseCode = "400", description = "Invalid input parameters"),
            @ApiResponse(responseCode = "500", description = "Internal server error")
    })
    @PostMapping(value = "/batch-process", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<?> processBatchDocuments(
            @Parameter(description = "List of portfolio document files to process", required = true) @RequestParam("files") List<MultipartFile> files,
            @Parameter(description = "Type of documents being processed", required = true) @RequestParam("documentType") DocumentType documentType,
            @Parameter(description = "Portfolio ID (optional)", required = false) @RequestParam(value = "portfolioId", required = false) String portfolioId,
            @Parameter(description = "Explicit Broker Type (optional)", required = false) @RequestParam(value = "brokerType", required = false) String brokerTypeStr) {

        String userId = resolveUserId();

        log.info("Batch processing {} documents for user: {}, type: {}, portfolio: {}, broker: {}",
                files.size(), userId, documentType, portfolioId, brokerTypeStr);

        try {
            List<DocumentProcessResponse> responses = documentProcessorService.processBatchDocuments(
                    files,
                    documentType,
                    portfolioId,
                    brokerTypeStr,
                    userId
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
        throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "User not authenticated or token missing");
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
