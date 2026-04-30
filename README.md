# AM Doc Intelligence

A unified monorepo for document processing, media management, and intelligence services.

## Overview

This repository consolidates several services related to document and media handling:

### Services
- **Cloudinary Manager** (`services/am-cloudinary-manager`): Java/Spring Boot service for media upload and signature management using Cloudinary.
- **Document Processor** (`services/am-document-processor`): Java/Spring Boot service for parsing and processing various document types (PDF, Excel, CSV).
- **Email Extractor** (`services/am-email-extractor`): Python/Flask service for extracting document data from Gmail and broker statements.

### Applications
- **Doc Viewer UI** (`apps/am-doc-viewer-ui`): Flutter web application for interacting with the document and email extraction services.

## Getting Started

### Prerequisites
- Docker and Docker Compose
- Java 17+ (for backend development)
- Python 3.10+ (for email extractor)
- Flutter SDK (for UI development)

### Running with Docker

1. Clone the repository and navigate to the root:
   ```bash
   cd am-doc-intelligence
   ```

2. Copy the example environment file and update your secrets:
   ```bash
   cp .env.example .env
   ```

3. Build and start the services:
   ```bash
   docker-compose up --build
   ```

## Repository Structure

```text
am-doc-intelligence/
├── apps/
│   └── am-doc-viewer-ui/       # Flutter Web Application
├── services/
│   ├── am-cloudinary-manager/  # Cloudinary Integration Service (Java)
│   ├── am-document-processor/  # Document Parsing Service (Java)
│   └── am-email-extractor/     # Gmail/Broker Extractor (Python)
├── docker-compose.yml          # Unified deployment configuration
└── .env.example                # Shared environment variables template
```

## CI/CD and Dependencies

### Common JARs
This repository depends on several common libraries hosted on GitHub Packages:
- `am-common-data-mongo`
- `am-common-data-model`
- `am-common-data-service`

To build locally, you must ensure your `~/.m2/settings.xml` has a server entry for `github` and `github-investment` with your GitHub Personal Access Token (PAT).

### CI/CD Pipeline
The services in this repository use the central pipeline defined in `AM-Portfolio/am-pipelines`.
- **Workflows**: Located in `.github/workflows/`
- **Maven Authentication**: Handled automatically in CI via `GITHUB_TOKEN` secrets and a dynamically generated `settings.xml`.

## License
Private / AM Portfolio
