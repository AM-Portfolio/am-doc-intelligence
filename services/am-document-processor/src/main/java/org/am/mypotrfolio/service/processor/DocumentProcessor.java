package org.am.mypotrfolio.service.processor;

import org.am.mypotrfolio.domain.common.DocumentRequest;
import org.am.mypotrfolio.model.DocumentProcessResponse;

import com.am.common.amcommondata.model.enums.BrokerType;

public interface DocumentProcessor {
    DocumentProcessResponse processDocument(DocumentRequest documentRequest, String portfolioId, String userId);
    BrokerType getBrokerType();
}
