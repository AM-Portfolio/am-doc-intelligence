package com.amportfolio.cloudinary.api.config;

import com.fasterxml.jackson.databind.JavaType;
import io.swagger.v3.core.converter.AnnotatedType;
import io.swagger.v3.core.converter.ModelConverter;
import io.swagger.v3.core.converter.ModelConverterContext;
import io.swagger.v3.oas.models.media.Schema;
import io.swagger.v3.oas.models.media.StringSchema;
import org.springframework.stereotype.Component;

import java.util.Arrays;
import java.util.Iterator;
import java.util.List;
import java.util.stream.Collectors;

@Component
public class EnumModelConverter implements ModelConverter {
    @Override
    public Schema resolve(AnnotatedType type, ModelConverterContext context, Iterator<ModelConverter> chain) {
        if (type.isSchemaProperty()) {
            JavaType _type = io.swagger.v3.core.util.Json.mapper().constructType(type.getType());
            if (_type != null) {
                Class<?> cls = _type.getRawClass();
                // ONLY process enums from your specific domain models package
                if (cls != null && cls.isEnum() && cls.getPackage() != null && cls.getPackage().getName().startsWith("com.amportfolio.cloudinary.model")) {
                    StringSchema schema = new StringSchema();
                    
                    // Extract exact enum constant names
                    List<String> values = Arrays.stream(cls.getEnumConstants())
                            .map(c -> ((Enum<?>) c).name())
                            .collect(Collectors.toList());
                            
                    // This creates the explicit vector/array in the Swagger schema
                    schema.setEnum(values);
                    
                    // Force the visual formatting with brackets for Swagger UI
                    schema.setExample(values.toString());
                    schema.setDescription("Allowed values: " + values.toString());
                    
                    return schema;
                }
            }
        }
        if (chain.hasNext()) {
            return chain.next().resolve(type, context, chain);
        }
        return null;
    }
}
