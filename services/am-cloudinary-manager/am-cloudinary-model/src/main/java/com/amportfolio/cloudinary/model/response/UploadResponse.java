package com.amportfolio.cloudinary.model.response;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

/**
 * Response model for Cloudinary upload operations
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UploadResponse {
    
    /**
     * Public ID of the uploaded resource
     */
    private String publicId;
    
    /**
     * URL of the uploaded resource
     */
    private String url;
    
    /**
     * Secure URL of the uploaded resource (HTTPS)
     */
    private String secureUrl;
    
    /**
     * Original filename
     */
    private String originalFilename;
    
    /**
     * Format of the uploaded resource
     */
    private String format;
    
    /**
     * Size of the uploaded resource in bytes
     */
    private Long bytes;
    
    /**
     * Resource type (image, video, raw, etc.)
     */
    private String resourceType;
    
    /**
     * Creation timestamp
     */
    @io.swagger.v3.oas.annotations.media.Schema(type = "string", format = "date-time", example = "2023-10-24T12:00:00Z")
    private java.time.Instant createdAt;
    
    /**
     * Additional metadata returned by Cloudinary
     */
    private Map<String, Object> metadata;
}
