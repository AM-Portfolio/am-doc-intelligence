package org.am.mypotrfolio.model.trade;

/**
 * Enum representing the type of trade (buy or sell)
 */
public enum TradeType {
    BUY("BUY"),
    SELL("SELL");

    private final String value;

    TradeType(String value) {
        this.value = value;
    }
}
