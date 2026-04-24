package org.am.mypotrfolio.kafka.model;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

import org.am.mypotrfolio.model.trade.TradeModel;

import com.am.common.amcommondata.model.enums.BrokerType;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Event model for trade updates to be sent via Kafka
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TradeUpdateEvent {
    private UUID id;
    private String userId;
    private BrokerType brokerType;
    private String portfolioId;
    private LocalDateTime timestamp;
    private List<TradeModel> trades;
}
