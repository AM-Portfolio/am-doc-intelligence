package org.am.mypotrfolio.service.impl;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.Optional;

import org.am.mypotrfolio.domain.common.MutualFundAsset;
import org.am.mypotrfolio.domain.common.DocumentRequest;
import org.am.mypotrfolio.domain.common.StockAsset;
import org.am.mypotrfolio.processor.FileProcessorFactory;
import org.am.mypotrfolio.service.PortfolioService;
import org.springframework.stereotype.Service;

import com.am.common.amcommondata.model.asset.equity.EquityModel;
import com.am.common.amcommondata.model.asset.mutualfund.MutualFundModel;
import com.am.common.amcommondata.model.enums.AssetType;
import com.am.common.amcommondata.model.enums.BrokerType;
import com.am.common.amcommondata.model.security.SecurityModel;
import com.am.common.amcommondata.service.SecurityService;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import lombok.RequiredArgsConstructor;
import lombok.SneakyThrows;
import lombok.extern.slf4j.Slf4j;

@Service("documentProcessorPortfolioService")
@Slf4j
@RequiredArgsConstructor
public class PortfolioServiceImpl implements PortfolioService {
    private final FileProcessorFactory fileProcessorFactory;
    private final SecurityService securityService;
    private final ObjectMapper objectMapper;

    @Override
    public List<EquityModel> processEquityFile(DocumentRequest portfolioRequest) {

        log.info("[ProcessId: {}] Starting to process stokcs portfolio file: {}", portfolioRequest.getRequestId(),
                portfolioRequest.getFile().getOriginalFilename());
        try {
            // Process the file using appropriate processor
            log.debug("[ProcessId: {}] Getting file processor for file type", portfolioRequest.getRequestId());
            List<Map<String, String>> fileData = fileProcessorFactory.getProcessor(portfolioRequest.getFile())
                    .processFile(portfolioRequest.getFile(), portfolioRequest);
            log.debug("[ProcessId: {}] Successfully processed file data, converting to StockPortfolio objects",
                    portfolioRequest.getRequestId());
            if (!fileData.isEmpty()) {
                log.info("[ProcessId: {}] First record keys: {}", portfolioRequest.getRequestId(),
                        fileData.get(0).keySet());
            }

            // Filter for Equity rows (Quantity field presence)
            List<Map<String, String>> equityData = fileData.stream()
                    .filter(row -> row.containsKey("Quantity"))
                    .toList();

            return processPortfolioFileAndGetAssets(equityData, portfolioRequest.getBrokerType(),
                    portfolioRequest.getRequestId());
        } catch (Exception e) {
            log.error("[ProcessId: {}] Error processing portfolio file: {}", portfolioRequest.getRequestId(),
                    e.getMessage(), e);
            throw e;
        }
    }

    @Override
    public List<MutualFundModel> processMutualFundFile(DocumentRequest portfolioRequest) {
        log.info("[ProcessId: {}] Starting to process mutual funds portfolio file: {}", portfolioRequest.getRequestId(),
                portfolioRequest.getFile().getOriginalFilename());
        try {
            // Process the file using appropriate processor
            log.debug("[ProcessId: {}] Getting file processor for file type", portfolioRequest.getRequestId());
            List<Map<String, String>> fileData = fileProcessorFactory.getProcessor(portfolioRequest.getFile())
                    .processFile(portfolioRequest.getFile(), portfolioRequest);
            log.debug("[ProcessId: {}] Successfully processed file data, converting to StockPortfolio objects",
                    portfolioRequest.getRequestId());

            // Filter for Mutual Fund rows (Units field presence)
            List<Map<String, String>> mfData = fileData.stream()
                    .filter(row -> row.containsKey("Units"))
                    .toList();

            return processMutualFundsPortfolioFileAndGetAssets(mfData, portfolioRequest.getBrokerType(),
                    portfolioRequest.getRequestId());
        } catch (Exception e) {
            log.error("[ProcessId: {}] Error processing portfolio file: {}", portfolioRequest.getRequestId(),
                    e.getMessage(), e);
            throw e;
        }
    }

    @SneakyThrows
    public List<MutualFundModel> processMutualFundsPortfolioFileAndGetAssets(List<Map<String, String>> fileData,
            BrokerType brokerType, UUID processId) {
        // Convert the data to StockPortfolio objects
        String payload = objectMapper.writeValueAsString(fileData);
        List<MutualFundAsset> portfolios = objectMapper.readValue(payload, new TypeReference<List<MutualFundAsset>>() {
        });
        // Convert to AssetModels
        List<MutualFundModel> portfolioAssets = new ArrayList<>();
        for (MutualFundAsset mutualFund : portfolios) {
            log.debug("[ProcessId: {}] Processing mutual funds: {}", processId, mutualFund.getSchemeName());
            // Try to find NSE security by name or other identifiers
            var assetModel = getMutualFundModel(mutualFund, brokerType);
            portfolioAssets.add(assetModel);
        }
        log.info("[ProcessId: {}] Successfully processed {} portfolio entries", processId, portfolioAssets.size());
        return portfolioAssets;
    }

    @SuppressWarnings("rawtypes")
    private MutualFundModel getMutualFundModel(MutualFundAsset mutualFund, BrokerType brokerType) {
        var quantity = getDouble(mutualFund.getUnits());
        var investedValue = mutualFund.getInvestedValue() != null ? getDouble(mutualFund.getInvestedValue()) : 0.0;
        var currentValue = mutualFund.getCurrentValue() != null ? getDouble(mutualFund.getCurrentValue()) : 0.0;
        MutualFundModel.MutualFundModelBuilder assetBuilder = MutualFundModel.builder()
                .assetType(AssetType.MUTUAL_FUND)
                .name(mutualFund.getSchemeName())
                .fundHouse(mutualFund.getAmc())
                .category(mutualFund.getCategory())
                .subCategory(mutualFund.getSubCategory())
                .quantity(round(quantity))
                .investmentValue(round(investedValue))
                .currentValue(round(currentValue));
        return assetBuilder.build();
    }

    @SneakyThrows
    public List<EquityModel> processPortfolioFileAndGetAssets(List<Map<String, String>> fileData, BrokerType brokerType,
            UUID processId) {
        // Convert the data to StockPortfolio objects
        String payload = objectMapper.writeValueAsString(fileData);
        List<StockAsset> portfolios = objectMapper.readValue(payload, new TypeReference<List<StockAsset>>() {
        });
        // Convert to AssetModels
        List<EquityModel> portfolioAssets = new ArrayList<>();
        boolean useDb = true;
        for (StockAsset stock : portfolios) {
            log.debug("[ProcessId: {}] Processing stock: {}", processId, stock.getSymbol());
            // Try to find NSE security by name or other identifiers
            try {
                var assetModel = getAssetModel(stock, brokerType, useDb);
                portfolioAssets.add(assetModel);
            } catch (RuntimeException e) {
                if ("DB_DOWN".equals(e.getMessage())) {
                    log.warn("Updates to DB failed, disabling DB for rest of processing");
                    useDb = false;
                    var assetModel = getAssetModel(stock, brokerType, false);
                    portfolioAssets.add(assetModel);
                } else {
                    throw e;
                }
            }
        }
        log.info("[ProcessId: {}] Successfully processed {} portfolio entries", processId, portfolioAssets.size());
        return portfolioAssets;
    }

    @SuppressWarnings("rawtypes")
    private EquityModel getAssetModel(StockAsset stock, BrokerType brokerType, boolean useDb) {
        var quantity = getDouble(stock.getQuantity());
        var avgBuyingPrice = stock.getAvgPrice() != null ? getDouble(stock.getAvgPrice()) : 0.0;
        var investedValue = stock.getInvestmentValue() != null ? getDouble(stock.getInvestmentValue())
                : quantity * avgBuyingPrice;
        EquityModel.EquityModelBuilder assetBuilder = EquityModel.builder()
                .assetType(AssetType.EQUITY)
                .isin(stock.getIsin())
                .symbol(stock.getSymbol())
                .avgBuyingPrice(round(avgBuyingPrice))
                .quantity(round(quantity))
                .investmentValue(round(investedValue))
                .name(stock.getName());

        if (useDb && brokerType != null
                && (brokerType.isDhan() || brokerType.isMStock() || brokerType.isGroww() || brokerType.isAngelOne())) {
            // Only try if we haven't failed before
            try {
                Optional<SecurityModel> nseSecurity = findBestMatchBySearchParam(
                        (brokerType.isDhan() || brokerType.isGroww() || brokerType.isAngelOne()) ? stock.getName()
                                : stock.getSymbol());
                if (nseSecurity.isPresent()) {
                    SecurityModel security = nseSecurity.get();
                    stock.setIsin(security.getKey().getIsin());
                }
            } catch (Exception e) {
                log.warn("Failed to find best match for stock: {} due to {}", stock.getSymbol(), e.getMessage());
                // Don't disable here as this might be specific to search
                throw new RuntimeException("DB_DOWN");
            }
        }

        // if (stock.getIsin() == null || stock.getIsin().isEmpty()) {
        if (useDb) {
            try {
                // Circuit breaker - skip if we know DB is down (simulated by simple check, or
                // just let first one fail)

                Optional<SecurityModel> nseSecurity = securityService.findByKey(stock.getIsin());
                // Enhance asset with NSE security information if available
                if (nseSecurity.isPresent()) {
                    SecurityModel security = nseSecurity.get();
                    assetBuilder.isin(security.getKey().getIsin());
                    assetBuilder.symbol(security.getKey().getSymbol());
                    assetBuilder.name(security.getMetadata().getSecurityName());
                    assetBuilder.industry(security.getMetadata().getIndustry());
                    assetBuilder.sector(security.getMetadata().getSector());
                    assetBuilder.marketCap(security.getMetadata().getMarketCapType().getName());
                }
            } catch (Exception e) {
                log.warn("Failed to enhance asset with NSE security info for ISIN: {} due to {}", stock.getIsin(),
                        e.getMessage());
                // We should rethrow or signal to caller to stop trying?
                throw new RuntimeException("DB_DOWN");
            }
        }
        // }
        return assetBuilder.build();
    }

    Optional<SecurityModel> findBestMatchBySearchParam(String searchParam) {
        if (searchParam == null || searchParam.trim().isEmpty()) {
            return Optional.empty();
        }
        List<SecurityModel> matches = securityService.findSecurityBySearchParam(searchParam);
        return matches.isEmpty() ? Optional.empty() : Optional.of(matches.get(0));
    }
}
