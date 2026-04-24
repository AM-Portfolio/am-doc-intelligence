package org.am.mypotrfolio.model;

import lombok.Data;
import java.util.UUID;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonInclude.Include;

@Data
@JsonInclude(Include.NON_NULL)
public class DocumentProcessResponse {
    private UUID processId;
    private String documentType;
    private String fileName;
    private ProcessingStatus status;
    private String message;
    private int totalRecords;
    private java.util.List<?> data;

}
