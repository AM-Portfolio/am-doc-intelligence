package com.amportfolio.cloudinary.model.request;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

/**
 * Request model for generating upload signatures
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SignatureRequest {
    
    /**
     * Public ID to use for the resource
     */
    private String publicId;
    
    /**
     * Folder path in Cloudinary where the file should be stored
     */
    private String folder;
    
    /**
     * Resource type (image, video, raw, etc.)
     */
    @Builder.Default
    private String resourceType = "auto";
    
    /**
     * Additional parameters for the upload
     */
    private Map<String, Object> params;
    
    /**
     * Timestamp for the signature (in seconds since epoch)
     * If not provided, current time will be used
     */
    private Long timestamp;
}
