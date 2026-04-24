package org.am.mypotrfolio.utils;

import com.fasterxml.jackson.annotation.JsonAutoDetect;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.PropertyAccessor;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.ObjectReader;
import com.fasterxml.jackson.databind.ObjectWriter;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;

import lombok.NoArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import reactor.core.publisher.Mono;

import org.springframework.core.io.ClassPathResource;
import org.springframework.core.io.Resource;
import org.springframework.util.StringUtils;

import java.io.IOException;
import java.io.InputStream;
import java.util.HashMap;
import java.util.Optional;

@Slf4j
@NoArgsConstructor
public class ObjectUtils {

    public static final <T> Optional<T> readJsonFile(TypeReference<T> typeReference, String payload) {
        ObjectMapper objectMapper = new ObjectMapper();
        try {
            Resource resource = new ClassPathResource(payload);
            InputStream input = resource.getInputStream();
            return Optional.of(objectMapper.readValue(input, typeReference));
        } catch (IOException e) {
            return Optional.empty();
        }
    }

    private static final ObjectReader objectReader = new ObjectMapper().registerModule(new JavaTimeModule())
            .setSerializationInclusion(JsonInclude.Include.NON_NULL)
            .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false)
            .reader();

    private static final ObjectWriter objectWriter = new ObjectMapper().registerModule(new JavaTimeModule())
            .setSerializationInclusion(JsonInclude.Include.NON_NULL)
            .setVisibility(PropertyAccessor.FIELD, JsonAutoDetect.Visibility.ANY)
            .writer();

    private static final TypeReference<HashMap<String, Object>> typeRef
            = new TypeReference<HashMap<String, Object>>() {
    };

    private static final ObjectReader reader = new ObjectMapper().readerFor(typeRef);
    public static <T> String writeObject(T t, String message) {
        try {
            return objectWriter.forType(t.getClass()).writeValueAsString(t);
        } catch (Exception e) {
            log.error("Exception while parsing {} with error message {}", message, e.getMessage());
        }
        return "";
    }



    public static <T> Optional<T> readObject(Class<T> object, String payload) {
        try {
            return Optional.of(objectReader.forType(object).readValue(payload));
        } catch (Exception e) {
            log.error("Exception while reading the json payload for {} with error message {}", object.getName(), e.getMessage());
            return Optional.empty();
        }
    }

    public static <T> String convertToJson(T object) {
        try {
            return objectWriter.forType(object.getClass()).writeValueAsString(object);
        } catch (Exception e) {
            throw new RuntimeException("Error converting object to JSON", e);
        }
    }


    public static <T> Mono<T> read(Class<T> object, String payload) {
        return Mono.defer(() -> readObject(object, payload)
                .map(Mono::just)
                .orElse(Mono.empty()));
    }

    public static <T> Optional <T> readObjects(TypeReference<T> typeReference, String payload) {
        if (StringUtils.isEmpty(payload))
            return Optional.empty();
        try {
            return Optional.of(objectReader.forType(typeReference).readValue(payload));
        } catch (Exception e) {
            log.error("Exception while reading the json list payload for {} with error message {}", typeReference.getType(), e.getMessage());
            return Optional.empty();
        }
    }

}
