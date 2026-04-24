package org.am.mypotrfolio.model.trade;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

import com.fasterxml.jackson.annotation.JsonAlias;
import com.fasterxml.jackson.annotation.JsonProperty;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Trade {
    @JsonProperty("symbol")
    @JsonAlias({ "Symbol", "symbol", "Scrip Name" })
    private String symbol;

    @JsonProperty("isin")
    @JsonAlias({ "ISIN", "isin", "ISIN Code" })
    private String isin;

    @JsonProperty("tradeDate")
    @JsonAlias({ "Trade Date", "tradeDate", "Date" })
    private LocalDate tradeDate;

    @JsonProperty("exchange")
    @JsonAlias({ "Exchange", "exchange" })
    private String exchange;

    @JsonProperty("segment")
    @JsonAlias({ "Segment", "segment" })
    private Segment segment;

    @JsonProperty("series")
    @JsonAlias({ "Series", "series" })
    private Series series;

    @JsonProperty("tradeType")
    @JsonAlias({ "Trade Type", "tradeType", "Type" })
    private String tradeType;

    @JsonProperty("auction")
    @JsonAlias({ "Auction", "auction" })
    private String auction;

    @JsonProperty("quantity")
    @JsonAlias({ "Quantity", "quantity", "Qty" })
    private BigDecimal quantity;

    @JsonProperty("price")
    @JsonAlias({ "Price", "price", "Rate" })
    private BigDecimal price;

    @JsonProperty("tradeId")
    @JsonAlias({ "Trade Id", "tradeId", "Trade ID" })
    private String tradeId;

    @JsonProperty("orderId")
    @JsonAlias({ "Order Id", "orderId", "Order ID" })
    private String orderId;

    @JsonProperty("orderExecutionTime")
    @JsonAlias({ "Order Execution Time", "orderExecutionTime", "Order Execution Time" })
    private LocalDateTime orderExecutionTime;
}