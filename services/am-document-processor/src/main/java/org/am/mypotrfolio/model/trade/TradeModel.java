package org.am.mypotrfolio.model.trade;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

import com.am.common.amcommondata.model.enums.BrokerType;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Model class representing a trade based on Zerodha's F&O trade book structure
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TradeModel {
    private BasicInfo basicInfo;
    private InstrumentInfo instrumentInfo;
    private ExecutionInfo executionInfo;
    private Charges charges;
    private Financials financials;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class BasicInfo {
        private String tradeId;
        private String orderId;
        private LocalDate tradeDate;
        private LocalDateTime orderExecutionTime;
        private BrokerType brokerType;
        private TradeType tradeType;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class InstrumentInfo {
        private String symbol;
        private String isin;
        private String exchange;
        private Segment segment;
        private Series series;
        private FnOInfo fnoInfo;
        
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ExecutionInfo {
        private TradeType tradeType;
        private String auction;
        private Integer quantity;
        private BigDecimal price;
        private Integer lotSize;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class FnOInfo {
        private FNOTradeType instrumentType; // FUTIDX, OPTIDX, FUTEQ, OPTEQ
        private LocalDate expiryDate;
        private BigDecimal strikePrice;
        private OptionType optionType; // CALL, PUT, NONE for futures
        private BigDecimal lotSize;
        private BigDecimal premiumValue;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Charges {
        private BigDecimal brokerage;
        private BigDecimal stt;
        private BigDecimal transactionCharges;
        private BigDecimal stampDuty;
        private BigDecimal sebiCharges;
        private BigDecimal gst;
        private BigDecimal totalTaxes;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Financials {
        private BigDecimal turnover;
        private BigDecimal netAmount;
    }
}
