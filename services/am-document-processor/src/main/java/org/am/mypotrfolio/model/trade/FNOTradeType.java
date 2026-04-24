package org.am.mypotrfolio.model.trade;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

import java.util.Arrays;

/**
 * Enum representing the type of F&O instrument
 */
public enum FNOTradeType {
    FUTIDX("FUTIDX", "Index Futures"),
    OPTIDX("OPTIDX", "Index Options"),
    FUTEQ("FUTEQ", "Equity Futures"),
    OPTEQ("OPTEQ", "Equity Options"),
    UNKNOWN("UNKNOWN", "Unknown Instrument Type");
    
    private final String value;
    private final String description;
    
    FNOTradeType(String value, String description) {
        this.value = value;
        this.description = description;
    }
    
    @JsonValue
    public String getValue() {
        return value;
    }
    
    public String getDescription() {
        return description;
    }
    
    @JsonCreator
    public static FNOTradeType fromValue(String value) {
        if (value == null) {
            return UNKNOWN;
        }
        
        return Arrays.stream(values())
                .filter(type -> type.value.equalsIgnoreCase(value))
                .findFirst()
                .orElse(UNKNOWN);
    }
}
