package org.am.mypotrfolio.domain.common;

import java.util.List;
import java.util.UUID;

import org.springframework.web.multipart.MultipartFile;

import com.am.common.amcommondata.model.enums.BrokerType;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DocumentRequest {

    private UUID requestId;
    private BrokerType brokerType;
    private String rawBrokerType;
    private DocumentType documentType;
    private MultipartFile file;
    private String portfolioId;
    private String userId;
    private String password;
}
