package org.am.mypotrfolio.model;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@Schema(description = "Request to process a document")
public class DocumentProcessRequest {
    @Schema(description = "Type of document", example = "STOCK_PORTFOLIO")
    private String documentType;
    
    @Schema(description = "Name of the file", example = "portfolio_jan.pdf")
    private String fileName;
    
    @Schema(description = "Binary content of the file", format = "binary")
    private byte[] fileContent;
}
