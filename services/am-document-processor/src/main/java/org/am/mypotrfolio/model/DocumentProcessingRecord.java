package org.am.mypotrfolio.model;

import com.am.common.amcommondata.model.enums.BrokerType;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.LocalDateTime;
import java.util.List;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Document(collection = "document_processing_records")
public class DocumentProcessingRecord {

    @Id
    private String processId;
    private String userId;
    private String portfolioId;
    private BrokerType brokerType;
    private String documentType;
    private String fileName;
    private int totalRecords;
    
    private List<?> data;
    
    @Builder.Default
    private LocalDateTime processedAt = LocalDateTime.now();
}
