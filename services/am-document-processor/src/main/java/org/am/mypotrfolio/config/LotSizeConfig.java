package org.am.mypotrfolio.config;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.HashMap;
import java.util.Map;
import java.util.NavigableMap;
import java.util.TreeMap;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;
import org.springframework.stereotype.Component;
import org.springframework.beans.factory.InitializingBean;

import lombok.Data;

/**
 * Configuration for lot sizes that can change over time
 * The configuration is loaded from application.yml
 */
@Data
@Component
@Configuration
@ConfigurationProperties(prefix = "trade.lot-sizes")
public class LotSizeConfig implements InitializingBean {
    
    private Map<String, Map<String, BigDecimal>> indices = new HashMap<>();
    private Map<String, BigDecimal> defaultLotSizes = new HashMap<>();
    
    // Cache for efficient lookup
    private Map<String, NavigableMap<LocalDate, BigDecimal>> lotSizeCache = new HashMap<>();
    
    /**
     * Initialize the cache after properties are set
     */
    @Override
    public void afterPropertiesSet() throws Exception {
        lotSizeCache.clear();
        
        // Process each index configuration
        for (Map.Entry<String, Map<String, BigDecimal>> indexEntry : indices.entrySet()) {
            String indexName = indexEntry.getKey();
            Map<String, BigDecimal> dateToLotSizeMap = indexEntry.getValue();
            
            NavigableMap<LocalDate, BigDecimal> timelineMap = new TreeMap<>();
            
            // Convert string dates to LocalDate for the timeline
            for (Map.Entry<String, BigDecimal> entry : dateToLotSizeMap.entrySet()) {
                LocalDate effectiveDate = LocalDate.parse(entry.getKey());
                timelineMap.put(effectiveDate, entry.getValue());
            }
            
            lotSizeCache.put(indexName.toUpperCase(), timelineMap);
        }
    }
    
    /**
     * Get the lot size for a given index on a specific date
     * 
     * @param indexName the name of the index (e.g., NIFTY, BANKNIFTY)
     * @param date the date for which to get the lot size
     * @return the lot size applicable on the given date, or default if not found
     */
    public BigDecimal getLotSize(String indexName, LocalDate date) {
        if (indexName == null || date == null) {
            return BigDecimal.ONE;
        }
        
        // Ensure cache is initialized
        if (lotSizeCache.isEmpty()) {
            try {
                afterPropertiesSet();
            } catch (Exception e) {
                // Handle exception or rethrow as runtime exception
                throw new RuntimeException("Failed to initialize lot size cache", e);
            }
        }
        
        NavigableMap<LocalDate, BigDecimal> timeline = lotSizeCache.get(indexName.toUpperCase());
        
        if (timeline != null && !timeline.isEmpty()) {
            // Get the entry with the greatest key less than or equal to the given date
            Map.Entry<LocalDate, BigDecimal> entry = timeline.floorEntry(date);
            if (entry != null) {
                return entry.getValue();
            }
        }
        
        // If no specific lot size found, return the default for this index
        BigDecimal defaultLotSize = defaultLotSizes.get(indexName.toUpperCase());
        return defaultLotSize != null ? defaultLotSize : BigDecimal.ONE;
    }
    
    /**
     * Get the current lot size for a given index
     * 
     * @param indexName the name of the index (e.g., NIFTY, BANKNIFTY)
     * @return the current lot size, or default if not found
     */
    public BigDecimal getCurrentLotSize(String indexName) {
        return getLotSize(indexName, LocalDate.now());
    }
}
