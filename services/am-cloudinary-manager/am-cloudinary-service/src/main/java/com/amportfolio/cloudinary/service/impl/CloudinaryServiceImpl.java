package com.amportfolio.cloudinary.service.impl;

import com.amportfolio.cloudinary.model.request.SignatureRequest;
import com.amportfolio.cloudinary.model.request.UploadRequest;
import com.amportfolio.cloudinary.model.response.SignatureResponse;
import com.amportfolio.cloudinary.model.response.UploadResponse;
import com.amportfolio.cloudinary.model.resource.CloudinaryResource;
import com.amportfolio.cloudinary.service.CloudinaryService;
import com.amportfolio.cloudinary.service.config.CloudinaryConfig;
import com.cloudinary.Cloudinary;
import com.cloudinary.api.ApiResponse;
import com.cloudinary.utils.ObjectUtils;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Base64;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Implementation of CloudinaryService
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class CloudinaryServiceImpl implements CloudinaryService {

    private final Cloudinary cloudinary;
    private final CloudinaryConfig cloudinaryConfig;

    @Override
    public UploadResponse uploadFile(UploadRequest request) throws IOException {
        try {
            // Prepare upload options
            Map<String, Object> options = new HashMap<>();
            
            // Set folder path (use default if not provided)
            String folder = org.springframework.util.StringUtils.hasText(request.getFolder()) ? 
                    request.getFolder() : cloudinaryConfig.getDefaultFolder();
            options.put("folder", folder);
            
            // Set overwrite option
            options.put("overwrite", request.getOverwrite());
            
            // Set resource type
            String resourceType = org.springframework.util.StringUtils.hasText(request.getResourceType()) ? 
                    request.getResourceType() : "auto";
            
            // Decode base64 content
            byte[] fileBytes = Base64.getDecoder().decode(request.getFileContent());
            
            // Upload to cloudinary
            @SuppressWarnings("unchecked")
            Map<String, Object> result = cloudinary.uploader().upload(
                    fileBytes,
                    ObjectUtils.asMap("resource_type", resourceType, "options", options)
            );
            
            log.info("Successfully uploaded file to Cloudinary: {}", request.getFilename());
            
            // Map response
            return UploadResponse.builder()
                    .publicId((String) result.get("public_id"))
                    .url((String) result.get("url"))
                    .secureUrl((String) result.get("secure_url"))
                    .originalFilename(request.getFilename())
                    .format((String) result.get("format"))
                    .bytes(((Number) result.get("bytes")).longValue())
                    .resourceType((String) result.get("resource_type"))
                    .createdAt((String) result.get("created_at"))
                    .metadata(result)
                    .build();
        } catch (IOException e) {
            log.error("Failed to upload file to Cloudinary: {}", e.getMessage(), e);
            throw e;
        }
    }

    @Override
    public CloudinaryResource getResource(String publicId, String resourceType) throws IOException {
        try {
            Map<String, Object> params = ObjectUtils.asMap("resource_type", resourceType);
            @SuppressWarnings("unchecked")
            Map<String, Object> result = cloudinary.api().resource(publicId, params);
            
            return mapToCloudinaryResource(result);
        } catch (Exception e) {
            log.error("Failed to get resource from Cloudinary: {}", e.getMessage(), e);
            throw new IOException("Failed to get resource from Cloudinary", e);
        }
    }

    @Override
    public List<CloudinaryResource> listResources(String folder, String resourceType, int maxResults) throws IOException {
        try {
            Map<String, Object> params = new HashMap<>();
            params.put("resource_type", resourceType);
            params.put("type", "upload");
            params.put("prefix", folder);
            params.put("max_results", maxResults);
            
            ApiResponse response = cloudinary.api().resources(params);
            
            List<CloudinaryResource> resources = new ArrayList<>();
            if (response.containsKey("resources")) {
                @SuppressWarnings("unchecked")
                List<Map<String, Object>> items = (List<Map<String, Object>>) response.get("resources");
                for (Map<String, Object> item : items) {
                    resources.add(mapToCloudinaryResource(item));
                }
            }
            
            return resources;
        } catch (Exception e) {
            log.error("Failed to list resources from Cloudinary: {}", e.getMessage(), e);
            throw new IOException("Failed to list resources from Cloudinary", e);
        }
    }

    @Override
    public Map<String, Object> deleteResource(String publicId, String resourceType) throws IOException {
        try {
            @SuppressWarnings("unchecked")
            Map<String, Object> result = cloudinary.uploader().destroy(
                    publicId,
                    ObjectUtils.asMap("resource_type", resourceType)
            );
            return result;
        } catch (Exception e) {
            log.error("Failed to delete resource from Cloudinary: {}", e.getMessage(), e);
            throw new IOException("Failed to delete resource from Cloudinary", e);
        }
    }
    
    @Override
    public SignatureResponse generateUploadSignature(SignatureRequest request) {
        try {
            // Create params map for signature
            Map<String, Object> params = new HashMap<>();
            
            // Add timestamp (use current time if not provided)
            long timestamp = request.getTimestamp() != null ? 
                    request.getTimestamp() : System.currentTimeMillis() / 1000;
            params.put("timestamp", timestamp);
            
            // Add folder if provided
            String folder = org.springframework.util.StringUtils.hasText(request.getFolder()) ? 
                    request.getFolder() : cloudinaryConfig.getDefaultFolder();
            params.put("folder", folder);
            
            // Add public_id if provided
            if (org.springframework.util.StringUtils.hasText(request.getPublicId())) {
                params.put("public_id", request.getPublicId());
            }
            
            // Add additional params if provided
            if (request.getParams() != null && !request.getParams().isEmpty()) {
                params.putAll(request.getParams());
            }
            
            // Generate the signature
            String signature = cloudinary.apiSignRequest(params, cloudinaryConfig.getApiSecret());
            
            // Determine resource type
            String resourceType = org.springframework.util.StringUtils.hasText(request.getResourceType()) ? 
                    request.getResourceType() : "auto";
            
            // Build upload URL
            String uploadUrl = String.format("https://api.cloudinary.com/v1_1/%s/%s/upload", 
                    cloudinaryConfig.getCloudName(), resourceType);
            
            // Create response
            return SignatureResponse.builder()
                    .apiKey(cloudinaryConfig.getApiKey())
                    .cloudName(cloudinaryConfig.getCloudName())
                    .signature(signature)
                    .timestamp(timestamp)
                    .publicId(request.getPublicId())
                    .folder(folder)
                    .resourceType(resourceType)
                    .uploadUrl(uploadUrl)
                    .params(request.getParams())
                    .build();
        } catch (Exception e) {
            log.error("Failed to generate upload signature: {}", e.getMessage(), e);
            throw new RuntimeException("Failed to generate upload signature", e);
        }
    }
    
    /**
     * Maps Cloudinary API response to CloudinaryResource model
     * 
     * @param resource the resource data from Cloudinary API
     * @return mapped CloudinaryResource
     */
    private CloudinaryResource mapToCloudinaryResource(Map<String, Object> resource) {
        return CloudinaryResource.builder()
                .publicId((String) resource.get("public_id"))
                .url((String) resource.get("url"))
                .secureUrl((String) resource.get("secure_url"))
                .format((String) resource.get("format"))
                .bytes(resource.get("bytes") != null ? ((Number) resource.get("bytes")).longValue() : null)
                .width(resource.get("width") != null ? ((Number) resource.get("width")).intValue() : null)
                .height(resource.get("height") != null ? ((Number) resource.get("height")).intValue() : null)
                .resourceType((String) resource.get("resource_type"))
                .createdAt((String) resource.get("created_at"))
                .folder((String) resource.get("folder"))
                .metadata(resource)
                .build();
    }
}
