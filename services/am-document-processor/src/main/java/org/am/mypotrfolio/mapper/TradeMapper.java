package org.am.mypotrfolio.mapper;

import org.am.mypotrfolio.model.trade.*;
import org.springframework.stereotype.Component;

import com.am.common.amcommondata.model.enums.BrokerType;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Mapper utility class for converting between Trade and TradeModel objects.
 */
@Component
public class TradeMapper {

    /**
     * Converts a Trade object to a TradeModel object.
     *
     * @param trade the Trade object to convert
     * @return the converted TradeModel object
     */
    public TradeModel toTradeModel(Trade trade, BrokerType brokerType) {
        if (trade == null) {
            return null;
        }

        return TradeModel.builder()
                .basicInfo(buildBasicInfo(trade, brokerType))
                .instrumentInfo(buildInstrumentInfo(trade))
                .executionInfo(buildExecutionInfo(trade))
                .build();
    }

    private TradeModel.BasicInfo buildBasicInfo(Trade trade, BrokerType brokerType) {
        TradeType type = null;
        if (trade.getTradeType() != null) {
            try {
                type = TradeType.valueOf(trade.getTradeType().toUpperCase());
            } catch (IllegalArgumentException e) {
                // Keep type as null if invalid
            }
        }

        return TradeModel.BasicInfo.builder()
                .tradeId(trade.getTradeId())
                .orderId(trade.getOrderId())
                .tradeDate(trade.getTradeDate())
                .orderExecutionTime(trade.getOrderExecutionTime())
                .brokerType(brokerType) // Set appropriate broker type if available
                .tradeType(type) // Set appropriate trade type if available
                .build();
    }

    private TradeModel.InstrumentInfo buildInstrumentInfo(Trade trade) {
        TradeModel.InstrumentInfo.InstrumentInfoBuilder builder = TradeModel.InstrumentInfo.builder()
                .symbol(trade.getSymbol())
                .isin(trade.getIsin())
                .exchange(trade.getExchange())
                .segment(trade.getSegment())
                .series(trade.getSeries());

        // If segment is F&O, add FnO info
        Segment segment = trade.getSegment();
        if (segment != null && (segment == Segment.FUTURES ||
                segment == Segment.OPTIONS ||
                segment == Segment.FNO ||
                "FO".equalsIgnoreCase(segment.getValue()))) {
            builder.fnoInfo(buildFnOInfo(trade));
        }

        return builder.build();
    }

    private TradeModel.ExecutionInfo buildExecutionInfo(Trade trade) {
        String symbol = trade.getSymbol();
        BigDecimal lotSize = determineLotSize(symbol, trade.getTradeDate());
        TradeType type = null;
        if (trade.getTradeType() != null) {
            try {
                type = TradeType.valueOf(trade.getTradeType().toUpperCase());
            } catch (IllegalArgumentException e) {
                // Keep type as null if invalid
            }
        }

        TradeModel.ExecutionInfo.ExecutionInfoBuilder executionInfoBuilder = TradeModel.ExecutionInfo.builder()
                .tradeType(type)
                .auction(trade.getAuction())
                .quantity(trade.getQuantity().intValue())
                .price(trade.getPrice());

        if (lotSize != null) {
            executionInfoBuilder.lotSize(trade.getQuantity().intValue() / lotSize.intValue());
        }

        return executionInfoBuilder.build();
    }

    /**
     * Builds FnO information by parsing the trade symbol.
     * Examples:
     * - RELIANCE20AUGFUT -> Equity Future
     * - BANKNIFTY20AUG23000PE -> Index Option
     *
     * @param trade the trade object
     * @return FnOInfo object with parsed details
     */
    /**
     * Extracts the expiry date from the symbol
     */
    private LocalDate extractExpiryDate(String symbol) {
        if (symbol == null || symbol.isEmpty())
            return null;

        try {
            // Pattern 1: Weekly/Short Monthly (YY M DD) -> e.g. 24215 (2024 Feb 15)
            // Matches: [Symbol][YY][M][DD][Strike][OptionType] or [Symbol][YY][M][DD][FUT]
            // We look for the date part specifically: 2 digits (Year), 1 char (1-9, O, N,
            // D), 2 digits (Day)
            // Regex explain: (\d{2})([1-9OND])(\d{2})
            // CAUTION: This might match strike prices or other numbers. Rely on valid date
            // context.
            // Better approach: Use the extraction logic from buildFnOInfo which isolates
            // the date part.
            // But if called standalone, we try strict patterns.

            // Pattern for Zerodha Weekly: SYMBOL + YY + M + DD + ...
            // e.g. NIFTY24215... -> 24 (Year), 2 (Feb), 15 (Day)
            // Extract using the same regex as buildFnOInfo would help.

            // Try standard monthly (DDMMMYY) first: 20AUG23
            Pattern stdPattern = Pattern.compile("(\\d{2})([A-Za-z]{3})(\\d{2})");
            Matcher stdMatcher = stdPattern.matcher(symbol);
            if (stdMatcher.find()) {
                String day = stdMatcher.group(1);
                String month = stdMatcher.group(2);
                String year = stdMatcher.group(3);
                return LocalDate.parse(day + "-" + month + "-20" + year, DateTimeFormatter.ofPattern("dd-MMM-yyyy"));
            }

            // Try short monthly (DDMMM): 20AUG
            Pattern shortStdPattern = Pattern.compile("(\\d{2})([A-Za-z]{3})");
            Matcher shortStdMatcher = shortStdPattern.matcher(symbol);
            if (shortStdMatcher.find()) { // Risk of false positives if strict structure not enforced
                // Usually at end or before FUT/CE/PE
            }

        } catch (DateTimeParseException e) {
            // Log error and return null
        }
        return null; // Logic moved to buildFnOInfo for better context
    }

    private TradeModel.FnOInfo buildFnOInfo(Trade trade) {
        String symbol = trade.getSymbol();
        if (symbol == null || symbol.isEmpty()) {
            return null;
        }

        TradeModel.FnOInfo.FnOInfoBuilder builder = TradeModel.FnOInfo.builder();
        String baseSymbol = symbol;
        LocalDate expiryDate = null;
        BigDecimal strikePrice = null;
        OptionType optionType = OptionType.NONE;
        FNOTradeType instrumentType = FNOTradeType.FUTIDX; // Default

        // Regex for Zerodha Weekly/Monthly: SYMBOL + YY(2) + M(1) + DD(2) + STRIKE +
        // CE/PE
        // M: 1-9 for Jan-Sep, O: Oct, N: Nov, D: Dec
        // D: 01-31 (Strict check to avoid matching "00")
        // Use non-greedy match for symbol to avoid eating into the year digits
        Pattern weeklyPattern = Pattern
                .compile("^([A-Z\\d&]+?)(\\d{2})([1-9OND])(0[1-9]|[12]\\d|3[01])(\\d+\\.?\\d*)(CE|PE)$");
        Matcher weeklyMatcher = weeklyPattern.matcher(symbol);

        // Regex for standard Monthly: SYMBOL + YY(2) + MMM(3) + STRIKE + CE/PE
        // e.g. BANKNIFTY23AUG44000CE
        Pattern monthlyPattern = Pattern.compile("^([A-Z\\d&]+?)(\\d{2})([A-Z]{3})(\\d+\\.?\\d*)(CE|PE)$");
        Matcher monthlyMatcher = monthlyPattern.matcher(symbol);

        // Regex for Futures: SYMBOL + YY + MMM + FUT
        Pattern futurePattern = Pattern.compile("^([A-Z\\d&]+?)(\\d{2})([A-Z]{3})FUT$");
        Matcher futureMatcher = futurePattern.matcher(symbol);

        if (weeklyMatcher.matches()) {
            // Weekly/Specific Date Option
            baseSymbol = weeklyMatcher.group(1);
            String year = weeklyMatcher.group(2);
            String monthChar = weeklyMatcher.group(3);
            String day = weeklyMatcher.group(4);
            String strike = weeklyMatcher.group(5);
            String opt = weeklyMatcher.group(6);

            int month = "OND".contains(monthChar) ? (monthChar.equals("O") ? 10 : (monthChar.equals("N") ? 11 : 12))
                    : Integer.parseInt(monthChar);

            expiryDate = LocalDate.of(2000 + Integer.parseInt(year), month, Integer.parseInt(day));
            strikePrice = new BigDecimal(strike);
            optionType = "CE".equalsIgnoreCase(opt) ? OptionType.CALL : OptionType.PUT;

        } else if (monthlyMatcher.matches()) {
            // Monthly Option
            baseSymbol = monthlyMatcher.group(1);
            String year = monthlyMatcher.group(2);
            String monthStr = monthlyMatcher.group(3);
            String strike = monthlyMatcher.group(4);
            String opt = monthlyMatcher.group(5);

            // Default day for monthly expiry is trickier without lookup, usually last
            // Thursday.
            // For now, we set it to 1st of month or handle as pure month-year if model
            // allows.
            // Or parse using a dummy day and adjust?
            // Simplification: Parse as 1st of month, user can imply expiry is month-end.
            try {
                expiryDate = LocalDate.parse("01-" + monthStr + "-20" + year,
                        DateTimeFormatter.ofPattern("dd-MMM-yyyy"));
                // Set to last day of month as approximation or leave as 1st?
                // Better: keep 1st to indicate "Month of".
                // Ideally we need a calendar utility to find last Thursday.
                expiryDate = expiryDate.withDayOfMonth(expiryDate.lengthOfMonth());
            } catch (Exception e) {
            }

            strikePrice = new BigDecimal(strike);
            optionType = "CE".equalsIgnoreCase(opt) ? OptionType.CALL : OptionType.PUT;

        } else if (futureMatcher.matches()) {
            // Future
            baseSymbol = futureMatcher.group(1);
            String year = futureMatcher.group(2);
            String monthStr = futureMatcher.group(3);

            try {
                expiryDate = LocalDate.parse("01-" + monthStr + "-20" + year,
                        DateTimeFormatter.ofPattern("dd-MMM-yyyy"));
                expiryDate = expiryDate.withDayOfMonth(expiryDate.lengthOfMonth());
            } catch (Exception e) {
            }

            optionType = OptionType.NONE;
        } else {
            // Fallback to old logic (suffix stripping) if regex fails
            // ... [Existing fallback logic can remain or be simplified]
            if (symbol.endsWith("CE") || symbol.endsWith("PE")) {
                optionType = symbol.endsWith("CE") ? OptionType.CALL : OptionType.PUT;
                // Try extracting strike from end
            }
        }

        // Determine Instrument Type (Index vs Stock)
        // Simple heuristic: NIFTY, BANKNIFTY, FINNIFTY are indices.
        boolean isIndex = isIndex(baseSymbol);
        if (optionType == OptionType.NONE) {
            instrumentType = isIndex ? FNOTradeType.FUTIDX : FNOTradeType.FUTEQ;
        } else {
            instrumentType = isIndex ? FNOTradeType.OPTIDX : FNOTradeType.OPTEQ;
        }

        builder.instrumentType(instrumentType)
                .expiryDate(expiryDate)
                .strikePrice(strikePrice)
                .optionType(optionType);

        // Set lot size based on trade date
        builder.lotSize(determineLotSize(symbol, trade.getTradeDate()));

        return builder.build();
    }

    /**
     * Extracts the base symbol from the F&O symbol
     */
    private String extractBaseSymbol(String symbol, String suffix) {
        // Remove the suffix and any date/month information
        String baseSymbol = symbol.replace(suffix, "");

        // Find where the date/month part starts (usually after letters)
        Pattern pattern = Pattern.compile("^([A-Za-z&]+)");
        Matcher matcher = pattern.matcher(baseSymbol);
        if (matcher.find()) {
            return matcher.group(1);
        }

        return baseSymbol;
    }

    /**
     * Determines if the symbol is an index
     */
    private boolean isIndex(String symbol) {
        return IndexType.isIndex(symbol);
    }

    /**
     * Determines the lot size based on the symbol and trade date
     * 
     * @param symbol    the trade symbol
     * @param tradeDate the date of the trade
     * @return the lot size applicable for the symbol on the given date
     */
    private BigDecimal determineLotSize(String symbol, LocalDate tradeDate) {
        String baseSymbol = extractBaseSymbol(symbol, "");
        return IndexType.getLotSizeForSymbol(baseSymbol, tradeDate);
    }

    /**
     * Determines the current lot size based on the symbol
     * 
     * @param symbol the trade symbol
     * @return the current lot size applicable for the symbol
     */
    private BigDecimal determineLotSize(String symbol) {
        return determineLotSize(symbol, LocalDate.now());
    }
}
