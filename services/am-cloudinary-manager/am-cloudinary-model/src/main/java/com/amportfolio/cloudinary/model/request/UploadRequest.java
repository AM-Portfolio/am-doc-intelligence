package com.amportfolio.cloudinary.model.request;

import jakarta.validation.constraints.NotBlank;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Request model for uploading files to Cloudinary
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UploadRequest {
    
    /**
     * Base64 encoded file content
     */
    @NotBlank(message = "File content is required")
    private String fileContent;
    
    /**
     * Filename with extension
     */
    @NotBlank(message = "Filename is required")
    private String filename;
    
    /**
     * Folder path in Cloudinary where the file should be stored
     */
    private String folder;
    
    /**
     * Whether to overwrite existing file with same public ID
     */
    @Builder.Default
    private Boolean overwrite = false;
    
    /**
     * Resource type (image, video, raw, etc.)
     */
    @Builder.Default
    private String resourceType = "auto";
}
