package org.am.mypotrfolio.model.trade;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.Arrays;

import org.am.mypotrfolio.config.LotSizeConfig;
import org.springframework.beans.BeansException;
import org.springframework.context.ApplicationContext;
import org.springframework.context.ApplicationContextAware;
import org.springframework.lang.NonNull;

/**
 * Enum representing different index types in the market
 */
public enum IndexType implements ApplicationContextAware {
    NIFTY("NIFTY", "Nifty 50"),
    BANKNIFTY("BANKNIFTY", "Bank Nifty"),
    FINNIFTY("FINNIFTY", "Financial Services Nifty"),
    MIDCPNIFTY("MIDCPNIFTY", "Midcap Nifty"),
    UNKNOWN("UNKNOWN", "Unknown Index");

    private static LotSizeConfig lotSizeConfig;
    
    private final String value;
    private final String description;
    
    IndexType(String value, String description) {
        this.value = value;
        this.description = description;
    }
    
    @Override
    public void setApplicationContext(@NonNull ApplicationContext applicationContext) throws BeansException {
        // This method will be called once for any enum constant
        // We only need to set the lotSizeConfig once
        if (IndexType.lotSizeConfig == null) {
            IndexType.lotSizeConfig = applicationContext.getBean(LotSizeConfig.class);
        }
    }

    @JsonValue
    public String getValue() {
        return value;
    }
    
    public String getDescription() {
        return description;
    }
    
    /**
     * Get the lot size for this index on the given date
     * 
     * @param date the date for which to get the lot size
     * @return the lot size applicable on the given date
     */
    public BigDecimal getLotSize(LocalDate date) {
        if (lotSizeConfig == null) {
            // Fallback to default values if config is not available
            switch (this) {
                case NIFTY: return new BigDecimal(50);
                case BANKNIFTY: return new BigDecimal(25);
                case FINNIFTY: return new BigDecimal(40);
                case MIDCPNIFTY: return new BigDecimal(75);
                default: return BigDecimal.ONE;
            }
        }
        return lotSizeConfig.getLotSize(this.value, date);
    }
    
    /**
     * Get the current lot size for this index
     * 
     * @return the current lot size
     */
    public BigDecimal getLotSize() {
        return getLotSize(LocalDate.now());
    }

    @JsonCreator
    public static IndexType fromValue(String value) {
        if (value == null) {
            return UNKNOWN;
        }
        
        return Arrays.stream(values())
                .filter(indexType -> indexType.value.equalsIgnoreCase(value))
                .findFirst()
                .orElse(UNKNOWN);
    }
    
    /**
     * Check if a symbol represents an index
     * 
     * @param symbol the symbol to check
     * @return true if the symbol is an index, false otherwise
     */
    public static boolean isIndex(String symbol) {
        if (symbol == null) {
            return false;
        }
        
        return Arrays.stream(values())
                .filter(indexType -> !indexType.equals(UNKNOWN))
                .anyMatch(indexType -> indexType.value.equalsIgnoreCase(symbol));
    }
    
    /**
     * Get the lot size for a given symbol on the given date
     * 
     * @param symbol the symbol to get the lot size for
     * @param date the date for which to get the lot size
     * @return the lot size for the symbol on the given date, or a default value if not found
     */
    public static BigDecimal getLotSizeForSymbol(String symbol, LocalDate date) {
        if (symbol == null) {
            return BigDecimal.ONE;
        }
        
        return Arrays.stream(values())
                .filter(indexType -> indexType.value.equalsIgnoreCase(symbol))
                .findFirst()
                .map(indexType -> indexType.getLotSize(date))
                .orElse(null); // Default lot size for equity
    }
    
    /**
     * Get the current lot size for a given symbol
     * 
     * @param symbol the symbol to get the lot size for
     * @return the current lot size for the symbol, or a default value if not found
     */
    public static BigDecimal getLotSizeForSymbol(String symbol) {
        return getLotSizeForSymbol(symbol, LocalDate.now());
    }
}
