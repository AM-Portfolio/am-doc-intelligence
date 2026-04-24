package org.am.mypotrfolio.model;

import lombok.Data;

@Data
public class DocumentProcessRequest {
    private String documentType;
    private String fileName;
    private byte[] fileContent;
}
