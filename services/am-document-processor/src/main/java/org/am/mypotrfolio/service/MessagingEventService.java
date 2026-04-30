package org.am.mypotrfolio.service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

import org.am.mypotrfolio.kafka.model.PortfolioUpdateEvent;
import org.am.mypotrfolio.kafka.model.TradeUpdateEvent;
import org.am.mypotrfolio.kafka.producer.KafkaProducerService;
import org.am.mypotrfolio.model.trade.FNOTradeType;
import org.am.mypotrfolio.model.trade.TradeModel;
import org.am.mypotrfolio.model.trade.TradeType;
import org.am.mypotrfolio.utils.ObjectUtils;
import org.springframework.stereotype.Service;

import com.am.common.amcommondata.model.asset.equity.EquityModel;
import com.am.common.amcommondata.model.asset.mutualfund.MutualFundModel;
import com.am.common.amcommondata.model.enums.BrokerType;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Service
@RequiredArgsConstructor
public class MessagingEventService {
    private final KafkaProducerService kafkaProducerService;

    public void sendStockPortfolioMessage(List<EquityModel> assetModels, UUID processId, BrokerType brokerType,
            String portfolioId, String userId) {
        log.info("[ProcessId: {}] Preparing to send stock portfolio update for user: {} and portfolio: {} (Count: {})", 
                processId, userId, portfolioId, assetModels.size());
        var portfolioUpdateEvent = buildPortfolioUpdateEvent(processId, brokerType, portfolioId, userId);
        portfolioUpdateEvent.setEquities(assetModels);
        kafkaProducerService.sendPortfolioUpdate(portfolioUpdateEvent);
        log.info("[ProcessId: {}] Successfully published stock portfolio update event to Kafka", processId);
    }

    public void sendMutualFundPortfolioMessage(List<MutualFundModel> mFundModels, UUID processId, BrokerType brokerType,
            String portfolioId, String userId) {
        log.info("[ProcessId: {}] Preparing to send mutual fund update for user: {} and portfolio: {} (Count: {})", 
                processId, userId, portfolioId, mFundModels.size());
        var portfolioUpdateEvent = buildPortfolioUpdateEvent(processId, brokerType, portfolioId, userId);
        portfolioUpdateEvent.setMutualFunds(mFundModels);
        kafkaProducerService.sendPortfolioUpdate(portfolioUpdateEvent);
        log.info("[ProcessId: {}] Successfully published mutual fund update event to Kafka", processId);
    }

    public void sendTradeFnoMessage(List<TradeModel> trades, UUID processId, BrokerType brokerType, String portfolioId,
            String userId) {
        log.info("[ProcessId: {}] Preparing to send F&O trade updates for user: {} and portfolio: {} (Count: {})", 
                processId, userId, portfolioId, trades.size());
        var tradeUpdateEvent = buildTradeUpdateEvent(processId, brokerType, portfolioId, userId);
        tradeUpdateEvent.setTrades(trades);
        kafkaProducerService.sendTradeUpdate(tradeUpdateEvent);
        log.info("[ProcessId: {}] Successfully published F&O trade update event to Kafka", processId);
    }

    private FNOTradeType extractTradeType(List<TradeModel> trades) {
        return trades.stream().findFirst().map(trade -> trade.getInstrumentInfo().getSegment()).map(segment -> {
            if (segment.equals("F")) {
                return FNOTradeType.FUTIDX;
            } else if (segment.equals("O")) {
                return FNOTradeType.OPTIDX;
            } else if (segment.equals("E")) {
                return FNOTradeType.FUTEQ;
            } else {
                return FNOTradeType.OPTEQ;
            }
        }).orElse(null);
    }

    public void sendTradeEqMessage(List<TradeModel> trades, UUID processId, BrokerType brokerType, String portfolioId,
            String userId) {
        log.info("[ProcessId: {}] Preparing to send Equity trade updates for user: {} and portfolio: {} (Count: {})", 
                processId, userId, portfolioId, trades.size());
        var tradeUpdateEvent = buildTradeUpdateEvent(processId, brokerType, portfolioId, userId);
        tradeUpdateEvent.setTrades(trades);
        kafkaProducerService.sendTradeUpdate(tradeUpdateEvent);
        log.info("[ProcessId: {}] Successfully published equity trade update event to Kafka", processId);
    }

    public void sendMessage(PortfolioUpdateEvent portfolioUpdateEvent, UUID processId, BrokerType brokerType) {
        log.info("[ProcessId: {}] Preparing to send portfolio update event and payload {}", processId,
                ObjectUtils.convertToJson(portfolioUpdateEvent));
        kafkaProducerService.sendPortfolioUpdate(portfolioUpdateEvent);
        log.info("[ProcessId: {}] Successfully sent portfolio update event", processId);
    }

    private PortfolioUpdateEvent buildPortfolioUpdateEvent(UUID processId, BrokerType brokerType, String portfolioId,
            String userId) {
        return PortfolioUpdateEvent.builder()
                .id(processId)
                .userId(userId)
                .brokerType(brokerType)
                .timestamp(LocalDateTime.now())
                .portfolioId(portfolioId)
                .build();
    }

    private TradeUpdateEvent buildTradeUpdateEvent(UUID processId, BrokerType brokerType, String portfolioId,
            String userId) {
        return TradeUpdateEvent.builder()
                .id(processId)
                .userId(userId)
                .brokerType(brokerType)
                .portfolioId(portfolioId)
                .timestamp(LocalDateTime.now())
                .build();
    }
}