package org.am.mypotrfolio.processor;

import com.opencsv.CSVReader;
import com.opencsv.CSVReaderBuilder;
import lombok.extern.slf4j.Slf4j;
import org.am.mypotrfolio.domain.common.DocumentType;
import org.springframework.stereotype.Component;
import org.springframework.web.multipart.MultipartFile;

import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.*;

@Slf4j
@Component
public class CsvFileProcessor extends AbstractFileProcessor {

    @Override
    public String getFileType() {
        return "CSV";
    }

    @Override
    public boolean canProcess(String fileExtension) {
        log.debug("Checking if can process file extension: {}", fileExtension);
        return fileExtension != null && fileExtension.equalsIgnoreCase("csv");
    }

    @Override
    protected List<Map<String, String>> parseDhanFile(MultipartFile file) throws Exception {
        return parseCsvFile(file, 0);
    }

    @Override
    protected List<Map<String, String>> parseMStockFile(MultipartFile file) throws Exception {
        return parseCsvFile(file, 0);
    }

    @Override
    protected List<Map<String, String>> parseZerodhaFile(MultipartFile file) throws Exception {
        return parseCsvWithHeaderDetection(file, new String[] { "Instrument", "Qty.", "Avg. cost" });
    }

    @Override
    protected List<Map<String, String>> parseGrowFile(MultipartFile file) throws Exception {
        return parseCsvFile(file, 20);
    }

    @Override
    protected List<Map<String, String>> parseGrowTradeFile(MultipartFile file, DocumentType docType)
            throws Exception {
        return new ArrayList<>();
    }

    @Override
    protected List<Map<String, String>> parseNseSecurityFile(MultipartFile file) throws Exception {
        return parseCsvFile(file, 0);
    }

    @Override
    protected List<Map<String, String>> parseZerodhaTradeFile(MultipartFile file) throws Exception {
        // Zerodha Tradebook usually has "symbol" and "trade_date" or "date"
        return parseCsvWithHeaderDetection(file, new String[] { "symbol", "trade_date", "quantity" });
    }

    @Override
    protected List<Map<String, String>> parseAngelOneFile(MultipartFile file, String password) throws Exception {
        return parseCsvFile(file, 0);
    }

    private List<Map<String, String>> parseCsvWithHeaderDetection(MultipartFile file, String[] possibleHeaders)
            throws Exception {
        List<Map<String, String>> data = new ArrayList<>();
        try (CSVReader reader = new CSVReaderBuilder(
                new InputStreamReader(file.getInputStream(), StandardCharsets.UTF_8))
                .build()) {

            String[] line;
            String[] headers = null;
            boolean headersFound = false;

            while ((line = reader.readNext()) != null) {
                if (!headersFound) {
                    // Check if this line is a header row
                    // We check if it contains any of the expected headers (case-insensitive)
                    // and doesn't look like data (numbers)
                    if (isHeaderRow(line, possibleHeaders)) {
                        headers = line;
                        // Clean headers (remove BOM, trim)
                        if (headers.length > 0 && headers[0].startsWith("\uFEFF")) {
                            headers[0] = headers[0].substring(1);
                        }
                        for (int i = 0; i < headers.length; i++) {
                            headers[i] = headers[i].trim();
                        }

                        // Normalize headers to match StockAsset fields
                        for (int i = 0; i < headers.length; i++) {
                            if ("Qty.".equalsIgnoreCase(headers[i])) {
                                headers[i] = "Quantity";
                            } else if ("Instrument".equalsIgnoreCase(headers[i])) {
                                headers[i] = "Symbol";
                            }
                        }

                        headersFound = true;
                        log.info("Detected headers: {}", Arrays.toString(headers));
                    }
                    continue;
                }

                // Process data rows
                Map<String, String> row = createRowData(headers, line);
                if (row != null) {
                    data.add(row);
                }
            }
            log.info("Successfully processed {} rows using smart detection", data.size());
        }
        return data;
    }

    private boolean isHeaderRow(String[] line, String[] likelyHeaders) {
        if (line == null || line.length == 0)
            return false;

        // Simple heuristic: check if line contains at least one likely header
        // and doesn't contain mostly numbers
        int matchCount = 0;
        for (String cell : line) {
            String cellVal = cell.trim().toLowerCase();
            for (String expected : likelyHeaders) {
                if (cellVal.contains(expected.toLowerCase())) {
                    matchCount++;
                }
            }
        }
        return matchCount > 0;
    }

    private List<Map<String, String>> parseCsvFile(MultipartFile file, int skipLines) throws Exception {
        List<Map<String, String>> data = new ArrayList<>();
        try (CSVReader reader = new CSVReaderBuilder(
                new InputStreamReader(file.getInputStream(), StandardCharsets.UTF_8))
                .withSkipLines(skipLines)
                .build()) {

            String[] headers = reader.readNext();
            if (headers != null) {
                // Remove BOM from the first header if present
                if (headers.length > 0 && headers[0].startsWith("\uFEFF")) {
                    headers[0] = headers[0].substring(1);
                }
                log.debug("Found headers: {}", Arrays.toString(headers));
                String[] line;
                int rowCount = 0;
                while ((line = reader.readNext()) != null) {
                    Map<String, String> row = createRowData(headers, line);
                    if (row != null) {
                        data.add(row);
                        rowCount++;
                    }
                }
                log.info("Successfully processed {} rows from CSV file", rowCount);
            } else {
                log.warn("No headers found in CSV file");
            }
        }
        return data;
    }
}
