package org.am.mypotrfolio.processor;

import lombok.extern.slf4j.Slf4j;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;
import org.springframework.stereotype.Component;
import org.springframework.web.multipart.MultipartFile;
import org.am.mypotrfolio.domain.common.DocumentRequest;
import com.am.common.amcommondata.model.enums.BrokerType;

import java.io.IOException;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Slf4j
@Component
public class PdfFileProcessor implements FileProcessor {

    @Override
    public String getFileType() {
        return "PDF";
    }

    @Override
    public boolean canProcess(String fileExtension) {
        return "pdf".equalsIgnoreCase(fileExtension);
    }

    @Override
    public List<Map<String, String>> processFile(MultipartFile file, DocumentRequest documentRequest) {
        log.info("Processing PDF file: {}", file.getOriginalFilename());
        try (PDDocument document = PDDocument.load(file.getInputStream())) {
            PDFTextStripper stripper = new PDFTextStripper();
            stripper.setSortByPosition(true); // Try to maintain layout
            String text = stripper.getText(document);

            // Log first 20 lines to understand structure
            String[] lines = text.split("\\r?\\n");
            log.info("PDF Content Preview (First 20 lines):");
            for (int i = 0; i < Math.min(lines.length, 20); i++) {
                log.info("Line {}: {}", i, lines[i]);
            }

            if (documentRequest.getBrokerType() != null && documentRequest.getBrokerType().isMStock()) {
                return parseMStockPdf(lines);
            }

            // Default fallback if no specific broker parser matches (or add other brokers
            // later)
            log.warn("No specific PDF parser found for broker: {}", documentRequest.getBrokerType());
            return Collections.emptyList();

        } catch (IOException e) {
            log.error("Failed to process PDF file", e);
            throw new RuntimeException("Failed to process PDF file", e);
        }
    }

    private List<Map<String, String>> parseMStockPdf(String[] lines) {
        log.info("Parsing MStock PDF content...");
        List<Map<String, String>> records = new ArrayList<>();

        // Strategy: Look for header line, then parse subsequent lines
        // Expected Header: Trade Date | Exchange | Buy/Sell | Scrip/Contract | Qty |
        // Price | Trade Id
        // Note: PDF text extraction might not preserve columns perfectly, usually
        // separated by spaces

        boolean headerFound = false;
        // MStock PDF usually has headers like "Trade Date Exchange Buy/Sell
        // Scrip/Contract Qty Price Trade Id"

        for (String line : lines) {
            String trimmed = line.trim();
            if (trimmed.isEmpty())
                continue;

            if (!headerFound) {
                if (trimmed.contains("Trade Date") && trimmed.contains("Exchange") && trimmed.contains("Scrip")) {
                    headerFound = true;
                    log.info("Found MStock Header: {}", trimmed);
                }
                continue;
            }

            // Processing data rows
            // Example Row: 19-08-2025 NSEEQ Sell BAJAJ-AUTO-EQ 5 8765.00 1053495
            // Columns might be merged if spaces are small, but let's assume space delimeter
            // for now
            // or we might need fixed width parsing if spaces vary.
            // Let's try flexible space splitting first.

            // Regex to match date at start: ^(\d{2}-\d{2}-\d{4})
            if (!trimmed.matches("^\\d{2}-\\d{2}-\\d{4}.*")) {
                // Skip lines that don't start with a date (e.g. footers, page numbers)
                continue;
            }

            try {
                // Split by multiple spaces
                String[] tokens = trimmed.split("\\s+");

                // MStock tokens likely:
                // 0: Date (19-08-2025)
                // 1: Exchange (NSEEQ)
                // 2: Type (Sell)
                // 3: Symbol (BAJAJ-AUTO-EQ) - might be multiple tokens if name has spaces?
                // Actually MStock uses hyphens usually for EQ, but let's be careful.
                // Looking at Excel: "BAJAJ-AUTO-EQ" -> single token likely.
                // But if scrip name has spaces e.g. "M & M", it might split.
                // Let's handle basic case first.
                // ...
                // Last 3 tokens: Qty, Price, TradeId

                if (tokens.length < 6) {
                    log.warn("Skipping malformed row (not enough tokens): {}", trimmed);
                    continue;
                }

                String date = tokens[0];
                String exchange = tokens[1];
                String type = tokens[2];

                // Extract last 3 known numeric/id fields
                String tradeId = tokens[tokens.length - 1]; // Trade Id
                String price = sanitizeNumeric(tokens[tokens.length - 2]); // Price
                String quantity = sanitizeNumeric(tokens[tokens.length - 3]); // Qty

                // Whatever is between Type and Qty is the Symbol
                // e.g. "BAJAJ-AUTO-EQ" -> 1 token
                // e.g. "M & M" -> 3 tokens
                int symbolStartIndex = 3;
                int symbolEndIndex = tokens.length - 3;

                StringBuilder symbolBuilder = new StringBuilder();
                for (int i = symbolStartIndex; i < symbolEndIndex; i++) {
                    if (symbolBuilder.length() > 0)
                        symbolBuilder.append(" ");
                    symbolBuilder.append(tokens[i]);
                }
                String symbol = symbolBuilder.toString();

                // Clean up symbol
                symbol = symbol.replace("-EQ", "").trim();

                // Normalize Date
                try {
                    java.time.LocalDate d = java.time.LocalDate.parse(date,
                            java.time.format.DateTimeFormatter.ofPattern("dd-MM-yyyy"));
                    date = d.format(java.time.format.DateTimeFormatter.ISO_LOCAL_DATE);
                } catch (Exception e) {
                    log.warn("Failed to parse date in PDF: {}", date);
                }

                Map<String, String> rowData = new HashMap<>();
                rowData.put("Trade Date", date);
                rowData.put("Symbol", symbol);
                rowData.put("Type", type);
                rowData.put("Quantity", quantity);
                rowData.put("Price", price);
                rowData.put("Exchange", exchange);

                records.add(rowData);

            } catch (Exception e) {
                log.warn("Error parsing PDF line: {}", trimmed, e);
            }
        }

        log.info("Parsed {} records from MStock PDF", records.size());
        return records;
    }

    private String sanitizeNumeric(String input) {
        if (input == null)
            return "0";
        return input.replaceAll("[^0-9.]", "");
    }

}
