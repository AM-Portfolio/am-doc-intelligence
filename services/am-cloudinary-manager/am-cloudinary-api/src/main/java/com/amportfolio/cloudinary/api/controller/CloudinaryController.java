package com.amportfolio.cloudinary.api.controller;

import com.amportfolio.cloudinary.model.request.SignatureRequest;
import com.amportfolio.cloudinary.model.request.UploadRequest;
import com.amportfolio.cloudinary.model.response.SignatureResponse;
import com.amportfolio.cloudinary.model.response.UploadResponse;
import com.amportfolio.cloudinary.model.resource.CloudinaryResource;
import com.amportfolio.cloudinary.service.CloudinaryService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Min;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.io.IOException;
import java.util.List;
import java.util.Map;

/**
 * REST controller for Cloudinary operations
 */
@RestController
@RequestMapping("/api/v1/cloudinary")
@RequiredArgsConstructor
@Validated
@Slf4j
@Tag(name = "Cloudinary API", description = "API for Cloudinary resource management")
public class CloudinaryController {

    private final CloudinaryService cloudinaryService;

    @PostMapping(value = "/upload", consumes = MediaType.APPLICATION_JSON_VALUE, produces = MediaType.APPLICATION_JSON_VALUE)
    @Operation(summary = "Upload a file to Cloudinary", description = "Uploads a file to Cloudinary using base64 encoded content")
    @ApiResponses(value = {
            @ApiResponse(responseCode = "201", description = "File uploaded successfully",
                    content = @Content(schema = @Schema(implementation = UploadResponse.class))),
            @ApiResponse(responseCode = "400", description = "Invalid request"),
            @ApiResponse(responseCode = "500", description = "Internal server error")
    })
    public ResponseEntity<UploadResponse> uploadFile(@Valid @RequestBody UploadRequest request) {
        try {
            UploadResponse response = cloudinaryService.uploadFile(request);
            return ResponseEntity.status(HttpStatus.CREATED).body(response);
        } catch (IOException e) {
            log.error("Failed to upload file: {}", e.getMessage(), e);
            throw new RuntimeException("Failed to upload file: " + e.getMessage(), e);
        }
    }

    @GetMapping(value = "/resources/{publicId}", produces = MediaType.APPLICATION_JSON_VALUE)
    @Operation(summary = "Get resource details", description = "Retrieves details of a specific resource by its public ID")
    @ApiResponses(value = {
            @ApiResponse(responseCode = "200", description = "Resource details retrieved successfully",
                    content = @Content(schema = @Schema(implementation = CloudinaryResource.class))),
            @ApiResponse(responseCode = "404", description = "Resource not found"),
            @ApiResponse(responseCode = "500", description = "Internal server error")
    })
    public ResponseEntity<CloudinaryResource> getResource(
            @PathVariable String publicId,
            @RequestParam(defaultValue = "image") String resourceType) {
        try {
            CloudinaryResource resource = cloudinaryService.getResource(publicId, resourceType);
            return ResponseEntity.ok(resource);
        } catch (IOException e) {
            log.error("Failed to get resource: {}", e.getMessage(), e);
            throw new RuntimeException("Failed to get resource: " + e.getMessage(), e);
        }
    }

    @GetMapping(value = "/resources", produces = MediaType.APPLICATION_JSON_VALUE)
    @Operation(summary = "List resources", description = "Lists resources in a specified folder")
    @ApiResponses(value = {
            @ApiResponse(responseCode = "200", description = "Resources listed successfully"),
            @ApiResponse(responseCode = "500", description = "Internal server error")
    })
    public ResponseEntity<List<CloudinaryResource>> listResources(
            @RequestParam(defaultValue = "uploads") String folder,
            @RequestParam(defaultValue = "image") String resourceType,
            @Parameter(description = "Maximum number of results to return")
            @RequestParam(defaultValue = "10") @Min(1) int maxResults) {
        try {
            List<CloudinaryResource> resources = cloudinaryService.listResources(folder, resourceType, maxResults);
            return ResponseEntity.ok(resources);
        } catch (IOException e) {
            log.error("Failed to list resources: {}", e.getMessage(), e);
            throw new RuntimeException("Failed to list resources: " + e.getMessage(), e);
        }
    }

    @DeleteMapping(value = "/resources/{publicId}", produces = MediaType.APPLICATION_JSON_VALUE)
    @Operation(summary = "Delete resource", description = "Deletes a resource by its public ID")
    @ApiResponses(value = {
            @ApiResponse(responseCode = "200", description = "Resource deleted successfully"),
            @ApiResponse(responseCode = "404", description = "Resource not found"),
            @ApiResponse(responseCode = "500", description = "Internal server error")
    })
    public ResponseEntity<Map<String, Object>> deleteResource(
            @PathVariable String publicId,
            @RequestParam(defaultValue = "image") String resourceType) {
        try {
            Map<String, Object> result = cloudinaryService.deleteResource(publicId, resourceType);
            return ResponseEntity.ok(result);
        } catch (IOException e) {
            log.error("Failed to delete resource: {}", e.getMessage(), e);
            throw new RuntimeException("Failed to delete resource: " + e.getMessage(), e);
        }
    }
    
    @PostMapping(value = "/signature", consumes = MediaType.APPLICATION_JSON_VALUE, produces = MediaType.APPLICATION_JSON_VALUE)
    @Operation(summary = "Generate upload signature", description = "Generates a signature for client-side uploads to Cloudinary")
    @ApiResponses(value = {
            @ApiResponse(responseCode = "200", description = "Signature generated successfully",
                    content = @Content(schema = @Schema(implementation = SignatureResponse.class))),
            @ApiResponse(responseCode = "400", description = "Invalid request"),
            @ApiResponse(responseCode = "500", description = "Internal server error")
    })
    public ResponseEntity<SignatureResponse> generateSignature(@Valid @RequestBody SignatureRequest request) {
        try {
            SignatureResponse response = cloudinaryService.generateUploadSignature(request);
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            log.error("Failed to generate signature: {}", e.getMessage(), e);
            throw new RuntimeException("Failed to generate signature: " + e.getMessage(), e);
        }
    }
}
