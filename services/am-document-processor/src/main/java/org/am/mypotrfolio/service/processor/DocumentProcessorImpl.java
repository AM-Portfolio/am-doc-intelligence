package org.am.mypotrfolio.service.processor;

import java.util.List;

import org.am.mypotrfolio.domain.common.DocumentRequest;
import org.am.mypotrfolio.model.DocumentProcessResponse;
import org.am.mypotrfolio.model.trade.TradeModel;
import org.am.mypotrfolio.service.MessagingEventService;
import org.am.mypotrfolio.service.NseService;
import org.am.mypotrfolio.service.PortfolioService;
import org.am.mypotrfolio.service.TradeService;
import org.am.mypotrfolio.repository.DocumentProcessingRecordRepository;
import org.am.mypotrfolio.model.DocumentProcessingRecord;
import org.springframework.stereotype.Component;

import com.am.common.amcommondata.model.asset.equity.EquityModel;
import com.am.common.amcommondata.model.asset.mutualfund.MutualFundModel;
import com.am.common.amcommondata.model.enums.BrokerType;
import com.am.common.amcommondata.model.security.SecurityModel;

import lombok.RequiredArgsConstructor;

@Component
@RequiredArgsConstructor
public class DocumentProcessorImpl implements DocumentProcessor {
    @org.springframework.beans.factory.annotation.Qualifier("documentProcessorPortfolioService")
    private final PortfolioService portfolioService;
    private final NseService nseService;
    private final MessagingEventService messagingEventService;
    private final TradeService tradeService;
    private final DocumentProcessingRecordRepository processingRecordRepository;

    @Override
    public DocumentProcessResponse processDocument(DocumentRequest documentRequest, String portfolioId, String userId) {
        List<?> data = processPortfolio(documentRequest, portfolioId, userId);
        DocumentProcessResponse response = new DocumentProcessResponse();
        response.setDocumentType(documentRequest.getDocumentType().name());
        response.setFileName(documentRequest.getFile().getOriginalFilename());
        response.setProcessId(documentRequest.getRequestId());
        response.setTotalRecords(data.size());
        response.setData(data);
        return response;
    }

    private List<?> processPortfolio(DocumentRequest documentRequest, String portfolioId, String userId) {
        if (documentRequest.getDocumentType().isStockPortfolio()) {
            return processEquityPortfolio(documentRequest, portfolioId, userId);
        } else if (documentRequest.getDocumentType().isMutualFund()) {
            return processMutualFundsPortfolio(documentRequest, portfolioId, userId);
        } else if (documentRequest.getDocumentType().isNseIndices()) {
            return processNseIndices(documentRequest, portfolioId);
        } else if (documentRequest.getDocumentType().isTradeFno()) {
            return processTradeFno(documentRequest, portfolioId, userId);
        } else if (documentRequest.getDocumentType().isTradeEq()) {
            return processTradeEq(documentRequest, portfolioId, userId);
        } else if (documentRequest.getDocumentType().isTradeMf()) {
            return processTradeMf(documentRequest, portfolioId, userId);
        } else if (documentRequest.getDocumentType().isCombinePortfolio()) {
            if (documentRequest.getBrokerType() == null || !documentRequest.getBrokerType().isAngelOne()) {
                throw new UnsupportedOperationException("Combine Portfolio is only supported for Angel One");
            }
            // Broker Portfolio can be Equity or Composite (Equity + MF)
            List<Object> combined = new java.util.ArrayList<>();
            combined.addAll(processEquityPortfolio(documentRequest, portfolioId, userId));
            combined.addAll(processMutualFundsPortfolio(documentRequest, portfolioId, userId));
            return combined;
        }
        return java.util.Collections.emptyList();
    }

    private List<EquityModel> processEquityPortfolio(DocumentRequest documentRequest, String portfolioId,
            String userId) {
        List<EquityModel> assets = portfolioService.processEquityFile(documentRequest);
        
        saveProcessingRecord(documentRequest, portfolioId, userId, assets);
        
        messagingEventService.sendStockPortfolioMessage(assets, documentRequest.getRequestId(),
                documentRequest.getBrokerType(), portfolioId, userId);
        return assets;
    }

    private List<SecurityModel> processNseIndices(DocumentRequest documentRequest, String portfolioId) {
        List<SecurityModel> assets = nseService.processNseSecurity(documentRequest);
        // messagingEventService.sendNseIndicesMessage(assets,
        // documentRequest.getRequestId(), documentRequest.getBrokerType());
        return assets;
    }

    private List<MutualFundModel> processMutualFundsPortfolio(DocumentRequest documentRequest, String portfolioId,
            String userId) {
        List<MutualFundModel> mutualFunds = portfolioService.processMutualFundFile(documentRequest);
        
        saveProcessingRecord(documentRequest, portfolioId, userId, mutualFunds);
        
        messagingEventService.sendMutualFundPortfolioMessage(mutualFunds, documentRequest.getRequestId(),
                documentRequest.getBrokerType(), portfolioId, userId);
        return mutualFunds;
    }

    private List<TradeModel> processTradeFno(DocumentRequest documentRequest, String portfolioId, String userId) {
        List<TradeModel> trades = tradeService.processTradeFile(documentRequest);
        
        saveProcessingRecord(documentRequest, portfolioId, userId, trades);
        
        messagingEventService.sendTradeFnoMessage(trades, documentRequest.getRequestId(),
                documentRequest.getBrokerType(), portfolioId, userId);
        return trades;
    }

    private List<TradeModel> processTradeEq(DocumentRequest documentRequest, String portfolioId, String userId) {
        List<TradeModel> trades = tradeService.processTradeFile(documentRequest);
        
        saveProcessingRecord(documentRequest, portfolioId, userId, trades);
        
        messagingEventService.sendTradeEqMessage(trades, documentRequest.getRequestId(),
                documentRequest.getBrokerType(), portfolioId, userId);
        return trades;
    }

    private List<TradeModel> processTradeMf(DocumentRequest documentRequest, String portfolioId, String userId) {
        // Reuse tradeService if it supports MF trades, or route to specific logic.
        // Assuming tradeService handles generic trade files or needs differentiation.
        // For now, mapping to sendTradeMfMessage (if exists) or generic trade message.
        // Let's assume tradeService can process it and we send a new event type.
        List<TradeModel> trades = tradeService.processTradeFile(documentRequest);
        
        saveProcessingRecord(documentRequest, portfolioId, userId, trades);
        
        // Fallback to EQ message for now until MF message is added to interface
        messagingEventService.sendTradeEqMessage(trades, documentRequest.getRequestId(),
                documentRequest.getBrokerType(), portfolioId, userId);
        return trades;
    }

    private void saveProcessingRecord(DocumentRequest documentRequest, String portfolioId, String userId, List<?> data) {
        try {
            DocumentProcessingRecord record = DocumentProcessingRecord.builder()
                    .processId(documentRequest.getRequestId().toString())
                    .userId(userId)
                    .portfolioId(portfolioId)
                    .brokerType(documentRequest.getBrokerType())
                    .documentType(documentRequest.getDocumentType().name())
                    .fileName(documentRequest.getFile().getOriginalFilename())
                    .totalRecords(data.size())
                    .data(data)
                    .build();
            processingRecordRepository.save(record);
        } catch (Exception e) {
            // Log but don't fail processing if DB tracking fails
            System.err.println("Failed to save processing record to MongoDB: " + e.getMessage());
        }
    }

    @Override
    public BrokerType getBrokerType() {
        return BrokerType.DHAN;
    }
}
