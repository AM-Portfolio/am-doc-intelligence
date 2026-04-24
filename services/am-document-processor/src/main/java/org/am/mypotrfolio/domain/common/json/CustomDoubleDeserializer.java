package org.am.mypotrfolio.domain.common.json;

import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.databind.DeserializationContext;
import com.fasterxml.jackson.databind.JsonDeserializer;
import java.io.IOException;

public class CustomDoubleDeserializer extends JsonDeserializer<Double> {
    @Override
    public Double deserialize(JsonParser p, DeserializationContext ctxt) throws IOException {
        String value = p.getText();
        if ("-".equals(value) || value.isEmpty()) {
            return null; // Return 0.0 if you prefer
        }
        try {
            return Double.valueOf(value);
        } catch (NumberFormatException e) {
            return null; // Or log the error and return a default value
        }
    }
}