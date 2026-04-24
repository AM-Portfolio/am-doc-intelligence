# Cloudinary API Postman Collection

This directory contains the Postman collection and JSON schemas for the Cloudinary API.

## Files

- **Cloudinary-API-Collection.postman_collection.json**: Complete Postman collection with all API endpoints
- **api-schemas.json**: JSON Schema definitions for all request/response models

## API Endpoints

### 1. Upload File
- **Method**: `POST`
- **Path**: `/api/v1/cloudinary/upload`
- **Description**: Upload a file to Cloudinary using base64 encoded content
- **Request Schema**: `UploadRequest`
- **Response Schema**: `UploadResponse`

### 2. Get Resource Details
- **Method**: `GET`
- **Path**: `/api/v1/cloudinary/resources/{publicId}`
- **Description**: Retrieve detailed information about a specific resource
- **Query Parameters**: `resourceType` (default: "image")
- **Response Schema**: `CloudinaryResource`

### 3. List Resources
- **Method**: `GET`
- **Path**: `/api/v1/cloudinary/resources`
- **Description**: List resources in a specified folder
- **Query Parameters**: 
  - `folder` (default: "uploads")
  - `resourceType` (default: "image")
  - `maxResults` (default: 10, minimum: 1)
- **Response Schema**: Array of `CloudinaryResource`

### 4. Delete Resource
- **Method**: `DELETE`
- **Path**: `/api/v1/cloudinary/resources/{publicId}`
- **Description**: Delete a specific resource from Cloudinary
- **Query Parameters**: `resourceType` (default: "image")
- **Response Schema**: `DeleteResponse`

### 5. Generate Upload Signature
- **Method**: `POST`
- **Path**: `/api/v1/cloudinary/signature`
- **Description**: Generate a cryptographic signature for client-side uploads
- **Request Schema**: `SignatureRequest`
- **Response Schema**: `SignatureResponse`

## How to Import

### Import Collection into Postman

1. Open Postman
2. Click **Import** button (top left)
3. Select **File** tab
4. Choose `Cloudinary-API-Collection.postman_collection.json`
5. Click **Import**

### Configure Environment Variables

The collection uses the following variables:

- `baseUrl`: Base URL of the API (default: `http://localhost:8080`)
- `publicId`: Public ID of a resource (automatically set after upload)
- `signature`: Generated signature (automatically set after signature generation)
- `timestamp`: Timestamp for signature (automatically set)
- `apiKey`: Cloudinary API key (automatically set)

To set up:

1. Create a new environment in Postman
2. Add the `baseUrl` variable with your server URL
3. Other variables are automatically populated by test scripts

## Request Examples

### Upload File Request
```json
{
  "fileContent": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
  "filename": "sample-image.png",
  "folder": "uploads",
  "overwrite": false,
  "resourceType": "auto"
}
```

### Generate Signature Request
```json
{
  "publicId": "uploads/my-custom-id",
  "folder": "uploads",
  "resourceType": "auto",
  "timestamp": null,
  "params": {
    "eager": "w_400,h_300,c_pad",
    "tags": "sample,client-upload"
  }
}
```

## Response Examples

### Upload Response
```json
{
  "publicId": "uploads/sample-image",
  "url": "http://res.cloudinary.com/demo/image/upload/v1234567890/uploads/sample-image.png",
  "secureUrl": "https://res.cloudinary.com/demo/image/upload/v1234567890/uploads/sample-image.png",
  "originalFilename": "sample-image.png",
  "format": "png",
  "bytes": 95,
  "resourceType": "image",
  "createdAt": "2025-11-29T10:30:00Z",
  "metadata": {
    "width": 1,
    "height": 1
  }
}
```

### Signature Response
```json
{
  "apiKey": "123456789012345",
  "publicId": "uploads/my-custom-id",
  "timestamp": 1732878600,
  "signature": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
  "cloudName": "demo",
  "folder": "uploads",
  "resourceType": "auto",
  "uploadUrl": "https://api.cloudinary.com/v1_1/demo/auto/upload",
  "params": {
    "eager": "w_400,h_300,c_pad",
    "tags": "sample,client-upload"
  }
}
```

## Test Scripts

Each request includes automated test scripts that:

- Verify response status codes
- Validate response structure
- Save relevant data to environment variables for subsequent requests
- Check for required fields

## Error Responses

All endpoints may return error responses with the following structure:

```json
{
  "timestamp": "2025-11-29T10:30:00Z",
  "status": 400,
  "error": "Bad Request",
  "message": "File content is required",
  "path": "/api/v1/cloudinary/upload"
}
```

Common HTTP status codes:
- `200 OK`: Successful GET/DELETE request
- `201 Created`: Successful upload
- `400 Bad Request`: Invalid request parameters
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server-side error

## JSON Schema Validation

The `api-schemas.json` file contains JSON Schema definitions for all models. You can use these schemas for:

- Request/response validation
- Documentation generation
- Code generation
- API contract testing

### Schema Definitions

- `UploadRequest`: Request body for file uploads
- `UploadResponse`: Response from upload operations
- `SignatureRequest`: Request body for signature generation
- `SignatureResponse`: Response from signature generation
- `CloudinaryResource`: Resource details model
- `DeleteResponse`: Response from delete operations
- `ErrorResponse`: Standard error response format

## Usage Tips

1. **Sequential Testing**: Run requests in order:
   - Generate Signature → Upload File → Get Resource → List Resources → Delete Resource

2. **Environment Variables**: The collection automatically saves `publicId` after upload, which is used by other endpoints

3. **Base64 Encoding**: For file uploads, ensure the `fileContent` includes the data URI prefix (e.g., `data:image/png;base64,...`)

4. **Resource Types**: Supported values: `image`, `video`, `raw`, `auto`

5. **Client-Side Uploads**: Use the signature endpoint to generate secure upload credentials for direct browser uploads

## Support

For issues or questions about the API, please refer to the main project documentation or contact the development team.
