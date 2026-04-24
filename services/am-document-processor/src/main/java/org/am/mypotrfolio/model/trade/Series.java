package org.am.mypotrfolio.model.trade;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

import java.util.Arrays;

public enum Series {
    EQ("EQ", "Equity"),
    BE("BE", "Book Entry"),
    BL("BL", "Block Deal"),
    BO("BO", "Buyout"),
    BT("BT", "Bond Trading"),
    GC("GC", "Government Securities"),
    IL("IL", "Index Linked"),
    IQ("IQ", "Interest Quote"),
    IT("IT", "Index Trading"),
    SM("SM", "SLB Market"),
    UNKNOWN("UNKNOWN", "Unknown Series");

    private final String value;
    private final String description;

    Series(String value, String description) {
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
    public static Series fromValue(String value) {
        if (value == null) {
            return UNKNOWN;
        }
        
        return Arrays.stream(values())
                .filter(series -> series.value.equalsIgnoreCase(value))
                .findFirst()
                .orElse(UNKNOWN);
    }
}
