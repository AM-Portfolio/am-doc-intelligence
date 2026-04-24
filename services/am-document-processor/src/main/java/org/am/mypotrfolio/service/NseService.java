package org.am.mypotrfolio.service;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import org.am.mypotrfolio.domain.common.NseSecurity;
import org.am.mypotrfolio.domain.common.DocumentRequest;

import org.am.mypotrfolio.processor.FileProcessorFactory;
import org.am.mypotrfolio.service.mapper.NseSecurityMapper;
import org.springframework.stereotype.Service;

import com.am.common.amcommondata.model.security.SecurityModel;
import com.am.common.amcommondata.service.SecurityService;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import lombok.RequiredArgsConstructor;
import lombok.SneakyThrows;
import lombok.extern.slf4j.Slf4j;

@Service
@Slf4j
@RequiredArgsConstructor
public class NseService {
    private final FileProcessorFactory fileProcessorFactory;
    private final NseSecurityMapper securityMapper;

    private final SecurityService securityService;
    private final ObjectMapper objectMapper;

    public List<SecurityModel> processNseSecurity(DocumentRequest documentRequest) {
        
        log.info("[ProcessId: {}] Starting to process stokcs portfolio file: {}", documentRequest.getRequestId(), documentRequest.getFile().getOriginalFilename());
        try {
            // Process the file using appropriate processor
            log.debug("[ProcessId: {}] Getting file processor for file type", documentRequest.getRequestId());
            //return processNseSecurityExcelFile(documentRequest.getFile());
             List<Map<String, String>> fileData = fileProcessorFactory.getProcessor(documentRequest.getFile())
                    .processFile(documentRequest.getFile(), null);
             log.debug("[ProcessId: {}] Successfully processed file data, converting to StockPortfolio objects", documentRequest.getRequestId());
            return processNseSecurityFile(fileData, documentRequest.getRequestId());
        } catch (Exception e) {
            log.error("[ProcessId: {}] Error processing portfolio file: {}", documentRequest.getRequestId(), e.getMessage(), e);
            throw e;
        }
    }

    @SneakyThrows
    public List<SecurityModel> processNseSecurityFile(List<Map<String, String>> fileData, UUID processId) {
        log.info("[ProcessId: {}] Starting to process NSE security file with {} entries", processId, fileData.size());
        
        log.debug("[ProcessId: {}] Converting file data to JSON", processId);
        String payload = objectMapper.writeValueAsString(fileData);
        
        log.debug("[ProcessId: {}] Parsing JSON data to NseSecurity objects", processId);
        List<NseSecurity> portfolios = objectMapper.readValue(payload, new TypeReference<List<NseSecurity>>() {});
        log.info("[ProcessId: {}] Successfully parsed {} NSE security entries", processId, portfolios.size());

        // Convert to SecurityModels
        List<SecurityModel> securityModels = new ArrayList<>();
        log.debug("[ProcessId: {}] Starting conversion to SecurityModels", processId);
        
        for (NseSecurity security : portfolios) {
            log.debug("[ProcessId: {}] Processing security: {} (ISIN: {})", processId, security.getSecurityId(), security.getIsin());

            // Try to find NSE security by name or other identifiers
            var securityModel = securityMapper.toSecurityModel(security);

            //@TODO: Find api/doc to provide realtime market data for all securities

            // equityDataRepository.findByKey(security.getIsin())
            //     .ifPresentOrElse(
            //         equityData -> {
            //             securityModel.getMetadata().setMarketCapValue(equityData.getMarketCap());
            //             log.debug("[ProcessId: {}] Found market cap data for security: {}", processId, security.getSecurityId());
            //         },
            //         () -> log.debug("[ProcessId: {}] No market cap data found for security: {}", processId, security.getSecurityId())
            //     );
            
            securityModels.add(securityModel);
        }

        log.debug("[ProcessId: {}] Saving {} security models to database", processId, securityModels.size());
        securityService.saveAll(securityModels);
        log.info("[ProcessId: {}] Successfully processed and saved {} NSE security entries", processId, securityModels.size());
        
        return securityModels;
    }
}
