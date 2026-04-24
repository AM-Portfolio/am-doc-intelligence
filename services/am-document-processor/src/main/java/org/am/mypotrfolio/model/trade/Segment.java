package org.am.mypotrfolio.model.trade;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

import java.util.Arrays;

public enum Segment {
    EQUITY("EQUITY"),
    FUTURES("FUTURES"),
    OPTIONS("OPTIONS"),
    CURRENCY("CURRENCY"),
    COMMODITY("COMMODITY"),
    FNO("FO"),
    UNKNOWN("UNKNOWN");

    private final String value;

    Segment(String value) {
        this.value = value;
    }

    @JsonValue
    public String getValue() {
        return value;
    }

    @JsonCreator
    public static Segment fromValue(String value) {
        if (value == null) {
            return UNKNOWN;
        }
        
        return Arrays.stream(values())
                .filter(segment -> segment.value.equalsIgnoreCase(value))
                .findFirst()
                .orElse(UNKNOWN);
    }
}
