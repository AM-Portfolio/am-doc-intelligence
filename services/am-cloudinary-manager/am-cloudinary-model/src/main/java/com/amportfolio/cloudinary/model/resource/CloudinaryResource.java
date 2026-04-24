package com.amportfolio.cloudinary.model.resource;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

/**
 * Model representing a Cloudinary resource
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CloudinaryResource {
    
    /**
     * Public ID of the resource
     */
    private String publicId;
    
    /**
     * URL of the resource
     */
    private String url;
    
    /**
     * Secure URL of the resource (HTTPS)
     */
    private String secureUrl;
    
    /**
     * Format of the resource
     */
    private String format;
    
    /**
     * Size of the resource in bytes
     */
    private Long bytes;
    
    /**
     * Width of the resource (for images and videos)
     */
    private Integer width;
    
    /**
     * Height of the resource (for images and videos)
     */
    private Integer height;
    
    /**
     * Resource type (image, video, raw, etc.)
     */
    private String resourceType;
    
    /**
     * Creation timestamp
     */
    private String createdAt;
    
    /**
     * Folder path in Cloudinary
     */
    private String folder;
    
    /**
     * Additional metadata
     */
    private Map<String, Object> metadata;
}
