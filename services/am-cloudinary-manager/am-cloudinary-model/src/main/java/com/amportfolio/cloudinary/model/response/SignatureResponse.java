package com.amportfolio.cloudinary.model.response;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

/**
 * Response model for Cloudinary upload signatures
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SignatureResponse {
    
    /**
     * API key for Cloudinary
     */
    private String apiKey;
    
    /**
     * Public ID to use for the resource
     */
    private String publicId;
    
    /**
     * Timestamp used for the signature (in seconds since epoch)
     */
    private Long timestamp;
    
    /**
     * Generated signature for the upload
     */
    private String signature;
    
    /**
     * Cloudinary cloud name
     */
    private String cloudName;
    
    /**
     * Folder path in Cloudinary where the file should be stored
     */
    private String folder;
    
    /**
     * Resource type (image, video, raw, etc.)
     */
    private String resourceType;
    
    /**
     * Upload URL for the resource type
     */
    private String uploadUrl;
    
    /**
     * Additional parameters for the upload
     */
    private Map<String, Object> params;
}
