package com.amportfolio.cloudinary.service;

import com.amportfolio.cloudinary.model.request.SignatureRequest;
import com.amportfolio.cloudinary.model.request.UploadRequest;
import com.amportfolio.cloudinary.model.response.SignatureResponse;
import com.amportfolio.cloudinary.model.response.UploadResponse;
import com.amportfolio.cloudinary.model.resource.CloudinaryResource;

import java.io.IOException;
import java.util.List;
import java.util.Map;

/**
 * Service interface for Cloudinary operations
 */
public interface CloudinaryService {

    /**
     * Upload a file to Cloudinary
     * 
     * @param request the upload request containing file data and options
     * @return upload response with resource details
     * @throws IOException if upload fails
     */
    UploadResponse uploadFile(UploadRequest request) throws IOException;
    
    /**
     * Get resource details by public ID
     * 
     * @param publicId the public ID of the resource
     * @param resourceType the resource type (image, video, raw, etc.)
     * @return resource details
     * @throws IOException if retrieval fails
     */
    CloudinaryResource getResource(String publicId, String resourceType) throws IOException;
    
    /**
     * List resources in a folder
     * 
     * @param folder the folder path
     * @param resourceType the resource type (image, video, raw, etc.)
     * @param maxResults maximum number of results to return
     * @return list of resources
     * @throws IOException if listing fails
     */
    List<CloudinaryResource> listResources(String folder, String resourceType, int maxResults) throws IOException;
    
    /**
     * Delete a resource by public ID
     * 
     * @param publicId the public ID of the resource
     * @param resourceType the resource type (image, video, raw, etc.)
     * @return deletion result
     * @throws IOException if deletion fails
     */
    Map<String, Object> deleteResource(String publicId, String resourceType) throws IOException;
    
    /**
     * Generate a signature for client-side upload to Cloudinary
     * 
     * @param request the signature request containing parameters for the upload
     * @return signature response with all required parameters for client-side upload
     */
    SignatureResponse generateUploadSignature(SignatureRequest request);
}
