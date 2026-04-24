package org.am.mypotrfolio.service.impl;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

import org.am.mypotrfolio.domain.common.DocumentRequest;
import org.am.mypotrfolio.mapper.TradeMapper;
import org.am.mypotrfolio.model.trade.Trade;
import org.am.mypotrfolio.model.trade.TradeModel;
import org.am.mypotrfolio.processor.FileProcessorFactory;
import org.am.mypotrfolio.service.TradeService;
import org.springframework.stereotype.Service;

import com.am.common.amcommondata.model.enums.BrokerType;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import lombok.RequiredArgsConstructor;
import lombok.SneakyThrows;
import lombok.extern.slf4j.Slf4j;

/**
 * Implementation of the TradeService for processing trade files
 * Based on Zerodha's F&O trade book structure
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class TradeServiceImpl implements TradeService {

    private final FileProcessorFactory fileProcessorFactory;
    private final ObjectMapper objectMapper;

    @Override
    public List<TradeModel> processTradeFile(DocumentRequest documentRequest) {

        log.info("[ProcessId: {}] Starting to process trade file: {}", documentRequest.getRequestId(),
                documentRequest.getFile().getOriginalFilename());
        try {
            // Process the file using appropriate processor
            log.debug("[ProcessId: {}] Getting file processor for file type", documentRequest.getRequestId());
            List<Map<String, String>> fileData = fileProcessorFactory.getProcessor(documentRequest.getFile())
                    .processFile(documentRequest.getFile(), documentRequest);
            log.debug("[ProcessId: {}] Successfully processed file data, converting to StockPortfolio objects",
                    documentRequest.getRequestId());
            return processTradeFileAndGetTradeList(fileData, documentRequest.getBrokerType(),
                    documentRequest.getRequestId());
        } catch (Exception e) {
            log.error("[ProcessId: {}] Error processing trade file: {}", documentRequest.getRequestId(), e.getMessage(),
                    e);
            throw e;
        }
    }

    @SneakyThrows
    public List<TradeModel> processTradeFileAndGetTradeList(List<Map<String, String>> fileData, BrokerType brokerType,
            UUID processId) {
        TradeMapper tradeMapper = new TradeMapper();
        if (!fileData.isEmpty()) {
            log.info("[ProcessId: {}] First record keys: {}", processId, fileData.get(0).keySet());
        }
        // Convert the data to StockPortfolio objects
        String payload = objectMapper.writeValueAsString(fileData);
        List<Trade> trades = objectMapper.readValue(payload, new TypeReference<List<Trade>>() {
        });

        // For Zerodha, aggregate trades with the same order ID
        if (BrokerType.ZERODHA.equals(brokerType)) {
            trades = aggregateZerodhaTrades(trades, processId);
        }

        // Convert to TradeModels
        List<TradeModel> tradeList = new ArrayList<>();
        for (Trade trade : trades) {
            log.debug("[ProcessId: {}] Processing trade: {}", processId, trade.getOrderId());
            TradeModel tradeModel = tradeMapper.toTradeModel(trade, brokerType);
            tradeList.add(tradeModel);
        }
        log.info("[ProcessId: {}] Successfully processed {} trade entries", processId, tradeList.size());
        return tradeList;
    }

    /**
     * Aggregates Zerodha trades with the same order ID.
     * For trades with the same order ID:
     * - Quantities are summed
     * - Prices are weighted averaged based on quantity
     * - Other attributes are taken from the first trade
     *
     * @param trades    List of trades to aggregate
     * @param processId Process ID for logging
     * @return List of aggregated trades
     */
    private List<Trade> aggregateZerodhaTrades(List<Trade> trades, UUID processId) {
        if (trades == null || trades.isEmpty()) {
            return trades;
        }

        log.debug("[ProcessId: {}] Aggregating Zerodha trades by order ID", processId);

        // Group trades by order ID
        Map<String, List<Trade>> tradesByOrderId = trades.stream()
                .filter(trade -> trade.getOrderId() != null && !trade.getOrderId().isEmpty())
                .collect(Collectors.groupingBy(Trade::getOrderId));

        List<Trade> aggregatedTrades = new ArrayList<>();

        // Process each group of trades with the same order ID
        for (Map.Entry<String, List<Trade>> entry : tradesByOrderId.entrySet()) {
            String orderId = entry.getKey();
            List<Trade> tradesWithSameOrderId = entry.getValue();

            if (tradesWithSameOrderId.size() == 1) {
                // If there's only one trade with this order ID, no need to aggregate
                aggregatedTrades.add(tradesWithSameOrderId.get(0));
            } else {
                // Aggregate trades with the same order ID
                Trade aggregatedTrade = aggregateTradesWithSameOrderId(tradesWithSameOrderId);
                aggregatedTrades.add(aggregatedTrade);
                log.debug("[ProcessId: {}] Aggregated {} trades with order ID: {}",
                        processId, tradesWithSameOrderId.size(), orderId);
            }
        }

        // Add any trades without order IDs
        trades.stream()
                .filter(trade -> trade.getOrderId() == null || trade.getOrderId().isEmpty())
                .forEach(aggregatedTrades::add);

        log.info("[ProcessId: {}] Aggregated {} trades into {} trades",
                processId, trades.size(), aggregatedTrades.size());

        return aggregatedTrades;
    }

    /**
     * Aggregates a list of trades with the same order ID into a single trade.
     *
     * @param trades List of trades with the same order ID
     * @return A single aggregated trade
     */
    private Trade aggregateTradesWithSameOrderId(List<Trade> trades) {
        if (trades == null || trades.isEmpty()) {
            return null;
        }

        // Use the first trade as the base
        Trade baseTrade = trades.get(0);

        // Calculate total quantity and weighted average price
        BigDecimal totalQuantity = BigDecimal.ZERO;
        BigDecimal weightedPriceSum = BigDecimal.ZERO;

        for (Trade trade : trades) {
            // Sum up quantities
            totalQuantity = totalQuantity.add(trade.getQuantity());

            // Calculate weighted price
            BigDecimal weightedPrice = trade.getPrice().multiply(trade.getQuantity());
            weightedPriceSum = weightedPriceSum.add(weightedPrice);
        }

        // Calculate weighted average price
        BigDecimal averagePrice = totalQuantity.compareTo(BigDecimal.ZERO) > 0
                ? weightedPriceSum.divide(totalQuantity, 2, RoundingMode.HALF_UP)
                : BigDecimal.ZERO;

        // Create a new aggregated trade
        return Trade.builder()
                .symbol(baseTrade.getSymbol())
                .isin(baseTrade.getIsin())
                .tradeDate(baseTrade.getTradeDate())
                .exchange(baseTrade.getExchange())
                .segment(baseTrade.getSegment())
                .series(baseTrade.getSeries())
                .tradeType(baseTrade.getTradeType())
                .auction(baseTrade.getAuction())
                .quantity(totalQuantity)
                .price(averagePrice)
                .tradeId(baseTrade.getTradeId())
                .orderId(baseTrade.getOrderId())
                .orderExecutionTime(baseTrade.getOrderExecutionTime())
                .build();
    }
}
