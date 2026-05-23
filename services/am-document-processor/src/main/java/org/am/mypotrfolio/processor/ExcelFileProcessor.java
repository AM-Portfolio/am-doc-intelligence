package org.am.mypotrfolio.processor;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

import org.apache.poi.ss.usermodel.*;
import java.util.stream.Collectors;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.springframework.stereotype.Component;
import org.springframework.web.multipart.MultipartFile;

import java.io.InputStream;
import java.util.*;

@Slf4j
@Component
@RequiredArgsConstructor
public class ExcelFileProcessor extends AbstractFileProcessor {

    @Override
    public String getFileType() {
        return "Excel";
    }

    @Override
    public boolean canProcess(String fileExtension) {
        log.debug("Checking if can process file extension: {}", fileExtension);
        return fileExtension != null &&
                (fileExtension.equalsIgnoreCase("xlsx") ||
                        fileExtension.equalsIgnoreCase("xls"));
    }

    @Override
    protected List<Map<String, String>> parseMStockFile(MultipartFile file) throws Exception {
        try (InputStream is = file.getInputStream();
                Workbook workbook = new XSSFWorkbook(is)) {

            Sheet sheet = workbook.getSheetAt(0);

            // Try to find "Trade Date" header
            int headerRow = findHeaderRow(sheet, "Trade Date", "Exchange");
            if (headerRow > 0 || (headerRow == 0
                    && "Trade Date".equalsIgnoreCase(getCellValueAsString(sheet.getRow(0).getCell(0))))) {
                log.info("Detected MStock Trade History format (Header at row {})", headerRow);
                return parseMStockTradeHistory(workbook, headerRow);
            }
        } catch (Exception e) {
            log.warn("Failed to inspect MStock file content, falling back to default", e);
        }

        return parseExcelFile(file, 0, 0, 0);
    }

    @Override
    protected List<Map<String, String>> parseZerodhaFile(MultipartFile file) throws Exception {
        return parseExcelFile(file, 22, 22, 1);
    }

    @Override
    protected List<Map<String, String>> parseDhanFile(MultipartFile file) throws Exception {
        int headerRow = 0;
        try (InputStream is = file.getInputStream();
                Workbook workbook = new XSSFWorkbook(is)) {
            Sheet sheet = workbook.getSheetAt(0);
            headerRow = findHeaderRow(sheet, "Scrip Name", "Quantity");
            if (headerRow == -1) {
                headerRow = findHeaderRow(sheet, "Scrip Name", "ISIN Code");
            }
            if (headerRow == -1) {
                log.warn("Dhan header not found, defaulting to row 0");
                headerRow = 0;
            }
        }

        List<Map<String, String>> rows = parseExcelFile(file, headerRow, headerRow, 0);
        List<Map<String, String>> cleanedRows = new ArrayList<>();

        for (Map<String, String> row : rows) {
            String scripName = row.getOrDefault("Scrip Name", "");
            if (scripName == null || scripName.trim().isEmpty())
                continue;

            // Skip footer/summary rows
            if (scripName.equalsIgnoreCase("Investment") || 
                scripName.equalsIgnoreCase("Current Value") ||
                scripName.contains("P&L") ||
                scripName.contains("NOTE :")) {
                continue;
            }

            // Handle older Dhan format with split quantity
            if (row.containsKey("Free Holding") && !row.containsKey("Quantity")) {
                try {
                    double free = Double.parseDouble(sanitizeNumeric(row.getOrDefault("Free Holding", "0")));
                    double locked = Double.parseDouble(sanitizeNumeric(row.getOrDefault("Locked In", "0")));
                    double mtf = Double.parseDouble(sanitizeNumeric(row.getOrDefault("MTF Pledge", "0")));
                    double margin = Double.parseDouble(sanitizeNumeric(row.getOrDefault("Margin Pledge", "0")));
                    row.put("Quantity", String.valueOf(free + locked + mtf + margin));
                } catch (Exception e) {
                    row.put("Quantity", row.get("Free Holding"));
                }
            }
            
            // Map "Avg. Buy Rate" to "Average Price" for Dhan Format B
            if (row.containsKey("Avg. Buy Rate") && !row.containsKey("Average Price")) {
                row.put("Average Price", row.get("Avg. Buy Rate"));
            }

            cleanedRows.add(row);
        }
        return cleanedRows;
    }

    @Override
    protected List<Map<String, String>> parseGrowFile(MultipartFile file) throws Exception {
        int headerRow = 0;
        try (InputStream is = file.getInputStream();
                Workbook workbook = new XSSFWorkbook(is)) {
            Sheet sheet = workbook.getSheetAt(0);
            headerRow = findHeaderRow(sheet, "Symbol", "Stock Name");
            if (headerRow == -1) {
                headerRow = 0; // Default to 0 if not found
            }
        }
        return parseExcelFile(file, headerRow, headerRow, 0);
    }

    @Override
    protected List<Map<String, String>> parseNseSecurityFile(MultipartFile file) throws Exception {
        return parseExcelFile(file, 0, 0, 0);
    }

    @Override
    protected List<Map<String, String>> parseZerodhaTradeFile(MultipartFile file) throws Exception {
        return parseZerodhaExcelFile(file);
    }

    private List<Map<String, String>> parseZerodhaExcelFile(MultipartFile file) throws Exception {
        List<Map<String, String>> jsonList = new ArrayList<>();
        try (InputStream is = file.getInputStream();
                Workbook workbook = new XSSFWorkbook(is)) {

            Sheet sheet = workbook.getSheetAt(0);

            // Find Header Row (Look for "Symbol" and "Trade Date")
            int headerRowIdx = findHeaderRow(sheet, "Symbol", "Trade Date", "ISIN");
            if (headerRowIdx == -1) {
                // Fallback to 14 if not found (based on file analysis)
                headerRowIdx = 14;
                log.warn("Zerodha header not found, defaulting to row {}", headerRowIdx);
            }

            Row headerRow = sheet.getRow(headerRowIdx);
            Map<String, Integer> colMap = new HashMap<>();

            // Map headers to column indices
            for (Cell cell : headerRow) {
                String header = getCellValueAsString(cell).trim();
                colMap.put(header.toLowerCase(), cell.getColumnIndex());
            }
            log.info("Zerodha Column Mapping: {}", colMap);

            int symbolIdx = colMap.getOrDefault("symbol", -1);
            int dateIdx = colMap.getOrDefault("trade date", -1);
            int typeIdx = colMap.getOrDefault("trade type", -1);
            int qtyIdx = colMap.getOrDefault("quantity", -1);
            int priceIdx = colMap.getOrDefault("price", -1);
            int exchangeIdx = colMap.getOrDefault("exchange", -1); // Usually 'NSE'/'BSE'
            int segmentIdx = colMap.getOrDefault("segment", -1); // 'EQ' / 'FO'

            if (symbolIdx == -1 || dateIdx == -1 || qtyIdx == -1) {
                log.error("Missing critical columns in Zerodha file. Found: {}", colMap.keySet());
                throw new IllegalArgumentException("Invalid Zerodha Trade File format. Sheet: " + sheet.getSheetName()
                        + ", Row: " + headerRowIdx + ", Found columns: " + colMap.keySet());
            }

            Iterator<Row> rowIterator = sheet.iterator();
            while (rowIterator.hasNext()) {
                Row row = rowIterator.next();
                if (row.getRowNum() <= headerRowIdx)
                    continue;

                String symbol = getCellValueAsString(row.getCell(symbolIdx));
                if (symbol.isEmpty())
                    continue;

                String dateStr = getCellValueAsString(row.getCell(dateIdx));
                // Zerodha date format: "2025-04-04" (yyyy-MM-dd) based on file inspection
                // But let's handle "dd-MM-yyyy" or "yyyy-MM-dd"
                try {
                    // If it's already ISO (yyyy-MM-dd), LocalDate.parse works
                    // If dd-MM-yyyy, we parse and format
                    if (dateStr.matches("\\d{2}-\\d{2}-\\d{4}")) {
                        java.time.LocalDate d = java.time.LocalDate.parse(dateStr,
                                java.time.format.DateTimeFormatter.ofPattern("dd-MM-yyyy"));
                        dateStr = d.format(java.time.format.DateTimeFormatter.ISO_LOCAL_DATE);
                    }
                } catch (Exception e) {
                    log.warn("Failed to parse Zerodha date: {}", dateStr);
                }

                String type = getCellValueAsString(row.getCell(typeIdx)); // "buy" / "sell"
                String qty = sanitizeNumeric(getCellValueAsString(row.getCell(qtyIdx)));
                String price = sanitizeNumeric(getCellValueAsString(row.getCell(priceIdx)));
                String exchange = getCellValueAsString(row.getCell(exchangeIdx));
                String segment = (segmentIdx != -1) ? getCellValueAsString(row.getCell(segmentIdx)) : "EQ";

                Map<String, String> rowData = new HashMap<>();
                rowData.put("Symbol", symbol);
                rowData.put("Trade Date", dateStr);
                rowData.put("Type", type);
                rowData.put("Quantity", qty);
                rowData.put("Price", price);
                rowData.put("Exchange", exchange);
                rowData.put("Segment", segment);

                jsonList.add(rowData);
            }
            log.info("Parsed {} records from Zerodha file", jsonList.size());
        }
        return jsonList;
    }

    @Override
    protected List<Map<String, String>> parseAngelOneFile(MultipartFile file, String password) throws Exception {
        return parseAngelOneExcelFile(file, password);
    }

    private List<Map<String, String>> parseAngelOneExcelFile(MultipartFile file, String password) throws Exception {
        List<Map<String, String>> jsonList = new ArrayList<>();
        Workbook workbook = null;
        InputStream inputStream = null;

        try {
            inputStream = file.getInputStream();
            // Try enabling decryption for password protected files
            try {
                if (password != null && !password.isEmpty()) {
                    workbook = WorkbookFactory.create(inputStream, password);
                    log.info("Opened workbook with provided password.");
                } else {
                    workbook = WorkbookFactory.create(inputStream);
                }
            } catch (org.apache.poi.EncryptedDocumentException e) {
                log.warn("Failed to open workbook. Encrypted? Password provided? Error: {}", e.getMessage());
                // Retry with hardcoded "JYQPK9320A" if user didn't provide one, just in case
                // (legacy support)
                if (password == null || password.isEmpty()) {
                    try {
                        inputStream.close();
                        inputStream = file.getInputStream();
                        workbook = WorkbookFactory.create(inputStream, "JYQPK9320A");
                        log.info("Opened workbook with legacy hardcoded password.");
                    } catch (Exception ex) {
                        // Rethrow original if fallback fails
                        throw e;
                    }
                } else {
                    throw e;
                }
            } catch (Exception e) {
                log.warn("Failed to open workbook: {}", e.getMessage());
                // If it fails or is not encrypted, try opening normally (re-open stream)
                if (inputStream.markSupported()) {
                    inputStream.reset();
                } else {
                    // Re-open stream if reset not supported
                    inputStream.close();
                    inputStream = file.getInputStream();
                }
                workbook = new XSSFWorkbook(inputStream);
            }

            // Check for Trade History format (Scan first 10 rows for ClientCode)
            Sheet firstSheet = workbook.getSheetAt(0);
            for (int i = 0; i < 10; i++) {
                Row row = firstSheet.getRow(i);
                if (row != null) {
                    String cellValue = getCellValueAsString(row.getCell(0));
                    log.info("Checking row {} for Trade History. Cell value: '{}'", i, cellValue);
                    if (cellValue != null && (cellValue.contains("ClientCode")
                            || cellValue.contains("Unique Client Code") || "Stock name".equalsIgnoreCase(cellValue)
                            || "Scrip/Contract".equalsIgnoreCase(cellValue))) {
                        log.info("Detected Angel One Trade/Order History file format at row {}", i);
                        return parseAngelOneTradeHistory(workbook);
                    }
                }
            }

            for (int i = 0; i < workbook.getNumberOfSheets(); i++) {
                Sheet sheet = workbook.getSheetAt(i);
                log.debug("Processing sheet: {}", sheet.getSheetName());

                Iterator<Row> rowIterator = sheet.iterator();
                String currentSection = "";

                while (rowIterator.hasNext()) {
                    Row row = rowIterator.next();
                    String firstCell = getCellValueAsString(row.getCell(0));

                    // Detect Section Headers
                    if (firstCell.contains("Equities Details") || firstCell.contains("Equity Holdings Details")) {
                        currentSection = "EQUITY";
                        log.info("Switched to EQUITY section at row {}", row.getRowNum());
                        continue;
                    } else if (firstCell.contains("Mutual Fund Details")) {
                        currentSection = "MF";
                        log.info("Switched to MF section at row {}", row.getRowNum());
                        continue;
                    } else if (firstCell.contains("Bond Details")) {
                        currentSection = "BOND";
                        log.info("Switched to BOND section at row {}", row.getRowNum());
                        continue;
                    }

                    if (currentSection.equals("EQUITY")) {
                        // Equity Structure: [Client ID, Script Name, ISIN, Qty, ...]
                        // Based on decrypted View: ISIN at col 2, Qty at col 3 (0-indexed based on
                        // likely header row)
                        // Validating strictly on ISIN presence
                        Cell isinCell = row.getCell(2);
                        if (isinCell != null) {
                            String isin = getCellValueAsString(isinCell);
                            log.trace("Checking Equity ISIN: {}", isin);
                            if (isin.startsWith("INE")) {
                                String name = getCellValueAsString(row.getCell(1));
                                String quantity = getCellValueAsString(row.getCell(5)); // Col 5
                                String avgPrice = getCellValueAsString(row.getCell(12)); // Col 12
                                String value = getCellValueAsString(row.getCell(15)); // Col 15

                                Map<String, String> rowData = new LinkedHashMap<>();
                                rowData.put("Name", name);
                                rowData.put("Scheme Name", name);
                                rowData.put("ISIN", isin);
                                rowData.put("Quantity", quantity);
                                // rowData.put("Units", quantity); // Removed to prevent false positive in MF
                                // filtering
                                rowData.put("Current Value", value);
                                rowData.put("Average Price", avgPrice);
                                jsonList.add(rowData);
                                log.debug("Added Equity: {} ({})", name, isin);
                            }
                        }
                    } else if (currentSection.equals("MF")) {
                        // Mutual Fund Structure: [Client ID, Scheme Name, ISIN, Units, ...]
                        // Based on decrypted View: ISIN at col 2, Units at col 3
                        Cell isinCell = row.getCell(2);
                        if (isinCell != null) {
                            String isin = getCellValueAsString(isinCell);
                            log.trace("Checking MF ISIN: {}", isin);
                            if (isin.startsWith("INF")) {
                                String name = getCellValueAsString(row.getCell(1));
                                String units = getCellValueAsString(row.getCell(3));
                                String nav = getCellValueAsString(row.getCell(4)); // Avg NAV (Cost)
                                String value = getCellValueAsString(row.getCell(7)); // Market Value

                                Map<String, String> rowData = new LinkedHashMap<>();
                                rowData.put("Scheme Name", name);
                                rowData.put("Name", name);
                                rowData.put("ISIN", isin);
                                rowData.put("Units", units);
                                // rowData.put("Quantity", units); // Removed to prevent false positive in
                                // Equity filtering
                                rowData.put("Current Value", value);
                                rowData.put("NAV", nav);
                                jsonList.add(rowData);
                            }
                        }
                    }
                }
            }
            log.info("Successfully parsed {} rows from Angel One Excel file", jsonList.size());
        } finally {
            if (workbook != null) {
                workbook.close();
            }
            if (inputStream != null) {
                inputStream.close();
            }
        }
        return jsonList;
    }

    private List<Map<String, String>> parseAngelOneTradeHistory(Workbook workbook) {
        List<Map<String, String>> jsonList = new ArrayList<>();
        Sheet sheet = workbook.getSheetAt(0);
        Iterator<Row> rowIterator = sheet.iterator();

        // Detect Header Row & Format
        int headerRowIndex = -1;
        boolean isOrderHistoryFormat = false; // true = "Stock name" format, false = "Scrip/Contract" format
        List<String> headers = new ArrayList<>();

        while (rowIterator.hasNext()) {
            Row row = rowIterator.next();
            if (row.getRowNum() > 40)
                break; // formatting likely within top 40 rows

            String firstCell = getCellValueAsString(row.getCell(0));
            if ("Scrip/Contract".equalsIgnoreCase(firstCell)) {
                headerRowIndex = row.getRowNum();
                isOrderHistoryFormat = false;
                log.info("Found Angel One Trade History (Format 1) Header at row: {}", headerRowIndex);
                break;
            } else if ("Stock name".equalsIgnoreCase(firstCell)) {
                headerRowIndex = row.getRowNum();
                isOrderHistoryFormat = true;
                log.info("Found Angel One Order History (Format 2) Header at row: {}", headerRowIndex);
                break;
            }
        }

        if (headerRowIndex == -1) {
            // Default to 33 if not found (legacy behavior)
            headerRowIndex = 33;
            log.warn("Angel One Header not found scan, defaulting to 33");
        }

        // Reset iterator to start
        rowIterator = sheet.iterator();

        while (rowIterator.hasNext()) {
            Row row = rowIterator.next();

            // Skip until header found (or if we are processing headers)
            if (row.getRowNum() < headerRowIndex)
                continue;

            if (row.getRowNum() == headerRowIndex) {
                // Read headers
                for (Cell cell : row) {
                    headers.add(getCellValueAsString(cell));
                }
                continue;
            }

            if (headers.isEmpty())
                continue;

            // Process Data Rows
            Map<String, String> rowData = new LinkedHashMap<>();

            if (isOrderHistoryFormat) {
                // FORMAT 2: ORDER HISTORY
                // Dynamic Column Mapping
                int stockNameIdx = -1, quantityIdx = -1, valueIdx = -1, dateIdx = -1, statusIdx = -1, symbolIdx = -1,
                        typeIdx = -1;

                // Map columns from headers
                for (int i = 0; i < headers.size(); i++) {
                    String h = headers.get(i).toLowerCase();
                    if (h.contains("stock name"))
                        stockNameIdx = i;
                    else if (h.contains("quantity"))
                        quantityIdx = i;
                    else if (h.contains("value") && !h.contains("date"))
                        valueIdx = i; // Avoid confusion with other value fields
                    else if (h.contains("execution date"))
                        dateIdx = i;
                    else if (h.contains("order status"))
                        statusIdx = i;
                    else if (h.contains("symbol"))
                        symbolIdx = i;
                    else if (h.contains("type") || h.equals("buy/sell"))
                        typeIdx = i;
                }

                // Fallback to defaults if not found (legacy support)
                if (dateIdx == -1)
                    dateIdx = 8;
                if (statusIdx == -1)
                    statusIdx = 9;
                if (quantityIdx == -1)
                    quantityIdx = 4;
                if (valueIdx == -1)
                    valueIdx = 5;
                if (symbolIdx == -1)
                    symbolIdx = 1;
                if (typeIdx == -1)
                    typeIdx = 3;

                // Check bounds
                if (row.getLastCellNum() <= Math.max(dateIdx, statusIdx))
                    continue;

                String status = getCellValueAsString(row.getCell(statusIdx));
                if (!"Executed".equalsIgnoreCase(status))
                    continue; // Filter non-executed

                String quantityStr = sanitizeNumeric(getCellValueAsString(row.getCell(quantityIdx)));
                if (quantityStr.isEmpty() || "0".equals(quantityStr))
                    continue;

                String symbol = getCellValueAsString(row.getCell(symbolIdx));
                String type = getCellValueAsString(row.getCell(typeIdx)); // BUY/SELL
                String valueStr = sanitizeNumeric(getCellValueAsString(row.getCell(valueIdx)));
                String dateStr = getCellValueAsString(row.getCell(dateIdx)); // "10-11-2022 02:00 PM"

                // Calculate Price = Value / Quantity
                try {
                    double qty = Double.parseDouble(quantityStr);
                    double val = Double.parseDouble(valueStr);
                    double price = (qty != 0) ? (val / qty) : 0.0;
                    rowData.put("Price", String.valueOf(price));
                } catch (Exception e) {
                    log.warn("Error calculating price for {}: val={}, qty={}", symbol, valueStr, quantityStr);
                    rowData.put("Price", "0");
                }

                rowData.put("Symbol", symbol);
                rowData.put("Type", type);
                rowData.put("Quantity", quantityStr);

                // Extract date part only (dd-MM-yyyy) and convert to yyyy-MM-dd for Jackson
                if (dateStr.contains(" ")) {
                    dateStr = dateStr.split(" ")[0];
                }
                try {
                    java.time.LocalDate date = java.time.LocalDate.parse(dateStr,
                            java.time.format.DateTimeFormatter.ofPattern("dd-MM-yyyy"));
                    dateStr = date.format(java.time.format.DateTimeFormatter.ISO_LOCAL_DATE);
                } catch (Exception e) {
                    log.warn("Failed to parse date: {}", dateStr);
                }
                rowData.put("Trade Date", dateStr);

            } else {
                // FORMAT 1: TRADE HISTORY (Legacy)
                // Dynamic Column Mapping
                int scripIdx = -1, typeIdx = -1, buyPriceIdx = -1, sellPriceIdx = -1, quantityIdx = -1, dateIdx = -1;

                for (int i = 0; i < headers.size(); i++) {
                    String h = headers.get(i).toLowerCase();
                    if (h.contains("scrip") || h.contains("contract"))
                        scripIdx = i;
                    else if (h.contains("buy/sell") || h.contains("transaction type"))
                        typeIdx = i;
                    else if (h.contains("buy price") || h.contains("buy rate"))
                        buyPriceIdx = i;
                    else if (h.contains("sell price") || h.contains("sell rate"))
                        sellPriceIdx = i;
                    else if (h.contains("quantity") || h.contains("qty"))
                        quantityIdx = i;
                    else if ((h.contains("date") && !h.contains("payout") && !h.contains("payin"))
                            || h.equals("trade date"))
                        dateIdx = i;
                }

                // Fallbacks
                if (scripIdx == -1)
                    scripIdx = 0;
                if (typeIdx == -1)
                    typeIdx = 1;
                if (buyPriceIdx == -1)
                    buyPriceIdx = 2;
                if (sellPriceIdx == -1)
                    sellPriceIdx = 3;
                if (quantityIdx == -1)
                    quantityIdx = 4;
                if (dateIdx == -1)
                    dateIdx = 17;

                // Check bounds
                if (row.getLastCellNum() <= Math.max(dateIdx, quantityIdx))
                    continue;

                String scrip = getCellValueAsString(row.getCell(scripIdx));
                // Skip empty or summary rows
                if (scrip.isEmpty() || scrip.contains("Grand Total") || scrip.contains("Total"))
                    continue;

                String quantityStr = getCellValueAsString(row.getCell(quantityIdx));
                // Skip if quantity is missing or 0
                if (quantityStr.isEmpty() || "0".equals(quantityStr))
                    continue;

                rowData.put("Symbol", scrip);
                rowData.put("Type", getCellValueAsString(row.getCell(typeIdx)));

                String buyPrice = getCellValueAsString(row.getCell(buyPriceIdx));
                String sellPrice = getCellValueAsString(row.getCell(sellPriceIdx));
                String priceRaw = !buyPrice.isEmpty() && !"0".equals(buyPrice) ? buyPrice : sellPrice;

                // Sanitize price (remove commas, handle empty)
                rowData.put("Price", sanitizeNumeric(priceRaw));
                rowData.put("Quantity", sanitizeNumeric(quantityStr));

                String dateStr = getCellValueAsString(row.getCell(dateIdx));
                // Normalize date if needed (usually dd-MMM-yyyy or dd/MM/yyyy in Format 1)
                // Angel One Trade History often uses "20-Jan-2023" or "20/01/2023"
                // Try to parse if it's not in standard ISO format
                if (dateStr.matches("\\d{2}-\\w{3}-\\d{4}")) { // e.g. 10-Nov-2022
                    try {
                        java.time.LocalDate date = java.time.LocalDate.parse(dateStr,
                                java.time.format.DateTimeFormatter.ofPattern("dd-MMM-yyyy"));
                        dateStr = date.format(java.time.format.DateTimeFormatter.ISO_LOCAL_DATE);
                    } catch (Exception e) {
                        log.warn("Failed to parse date (Format 1): {}", dateStr);
                    }
                }
                rowData.put("Trade Date", dateStr);
            }

            if (!rowData.isEmpty()) {
                jsonList.add(rowData);
            }
        }
        log.info("Parsed {} trade records from Angel One Trade History", jsonList.size());
        return jsonList;
    }

    private String sanitizeNumeric(String value) {
        if (value == null || value.trim().isEmpty()) {
            return "0";
        }
        return value.replace(",", "").trim();
    }

    private String getCellValueAsString(Cell cell) {
        if (cell == null)
            return "";
        switch (cell.getCellType()) {
            case STRING:
                return cell.getStringCellValue().trim();
            case NUMERIC:
                if (DateUtil.isCellDateFormatted(cell)) {
                    return cell.getLocalDateTimeCellValue().toString();
                }
                return String.valueOf(cell.getNumericCellValue());
            case BOOLEAN:
                return String.valueOf(cell.getBooleanCellValue());
            default:
                return "";
        }
    }

    private int findHeaderRow(Sheet sheet, String... keywords) {
        Iterator<Row> rowIterator = sheet.iterator();
        while (rowIterator.hasNext()) {
            Row row = rowIterator.next();
            if (row.getRowNum() > 20)
                break;

            // Iterate ALL cells in the row, not just the first one
            for (Cell cell : row) {
                String cellValue = getCellValueAsString(cell);
                for (String keyword : keywords) {
                    if (cellValue.equalsIgnoreCase(keyword)
                            || cellValue.toLowerCase().contains(keyword.toLowerCase())) {
                        return row.getRowNum();
                    }
                }
            }
        }
        log.warn("Header not found in first 20 rows, defaulting to -1");
        return -1;
    }

    private List<Map<String, String>> parseMStockTradeHistory(Workbook workbook, int headerRow) throws Exception {
        List<Map<String, String>> jsonList = new ArrayList<>();
        Sheet sheet = workbook.getSheetAt(0);

        // MStock Header is usually at row 16
        // Columns:
        // 0: Trade Date
        // 1: Exchange
        // 2: Buy / Sell -> Type
        // 3: Scrip / Contract -> Symbol
        // 4: Qty
        // 5: Price
        // 6: Trade Id

        log.info("Parsing MStock Trade History from sheet: {} with header at row {}", sheet.getSheetName(), headerRow);

        Iterator<Row> rowIterator = sheet.iterator();
        while (rowIterator.hasNext()) {
            Row row = rowIterator.next();
            // Skip rows before and including header
            if (row.getRowNum() <= headerRow)
                continue;

            String tradeDate = getCellValueAsString(row.getCell(0));
            // Stop if date is missing or doesn't look like a date (dd-MM-yyyy)
            if (tradeDate.isEmpty() || !tradeDate.matches("\\d{2}-\\d{2}-\\d{4}")) {
                log.debug("Skipping non-date row in MStock file: {}", tradeDate);
                continue;
            }

            Map<String, String> rowData = new HashMap<>();

            // Symbol cleanup: "BAJAJ-AUTO-EQ" -> "BAJAJ-AUTO"
            String symbol = getCellValueAsString(row.getCell(3)).replace("-EQ", "").trim();
            String type = getCellValueAsString(row.getCell(2)); // "Buy" or "Sell"
            String qty = sanitizeNumeric(getCellValueAsString(row.getCell(4)));
            String price = sanitizeNumeric(getCellValueAsString(row.getCell(5)));

            rowData.put("Symbol", symbol);
            rowData.put("Type", type);
            rowData.put("Quantity", qty);
            rowData.put("Price", price);
            rowData.put("Trade Date", tradeDate); // Format seems to be dd-MM-yyyy or dd-MM-yyyy

            // Date Normalization
            try {
                // "19-08-2025" -> dd-MM-yyyy
                java.time.LocalDate date = java.time.LocalDate.parse(tradeDate,
                        java.time.format.DateTimeFormatter.ofPattern("dd-MM-yyyy"));
                rowData.put("Trade Date", date.format(java.time.format.DateTimeFormatter.ISO_LOCAL_DATE));
            } catch (Exception e) {
                log.warn("Failed to parse date (MStock): {}", tradeDate);
            }

            jsonList.add(rowData);
        }

        log.info("Parsed {} trade records from MStock", jsonList.size());
        return jsonList;
    }

    private List<Map<String, String>> parseExcelFile(MultipartFile file, int headerRow, int skipRows, int skipColumns)
            throws Exception {
        List<Map<String, String>> jsonList = new ArrayList<>();

        try (InputStream inputStream = file.getInputStream();
                Workbook workbook = new XSSFWorkbook(inputStream)) {

            Sheet sheet = workbook.getSheetAt(0);

            log.debug("Reading sheet: {}", sheet.getSheetName());
            
            List<String> headers = new ArrayList<>();
            int rowCount = 0;

            // Get header row first to know how many columns we are dealing with
            Row hr = sheet.getRow(headerRow);
            if (hr == null) {
                log.warn("Header row {} is null", headerRow);
                return jsonList;
            }
            
            int lastCellNum = hr.getLastCellNum();
            for (int c = 0; c < lastCellNum; c++) {
                Cell cell = hr.getCell(c, Row.MissingCellPolicy.CREATE_NULL_AS_BLANK);
                cell.setCellType(CellType.STRING);
                String header = cell.getStringCellValue().trim();
                // Remove BOM if present
                if (headers.isEmpty() && header.startsWith("\uFEFF")) {
                    header = header.substring(1);
                }
                headers.add(header);
            }

            // Normalize headers to match StockAsset fields
            for (int i = 0; i < headers.size(); i++) {
                String h = headers.get(i);
                if ("Quantity Available".equalsIgnoreCase(h)) {
                    headers.set(i, "Quantity");
                }
            }

            // Adjust headers list if we need to skip columns
            List<String> finalHeaders = headers;
            if (skipColumns > 0 && skipColumns < headers.size()) {
                finalHeaders = headers.subList(skipColumns, headers.size());
            }

            // Iterate over data rows
            for (int r = skipRows + 1; r <= sheet.getLastRowNum(); r++) {
                Row row = sheet.getRow(r);
                if (row == null) {
                    continue;
                }

                String[] values = new String[finalHeaders.size()];
                int valueIndex = 0;
                int startCol = skipColumns;

                for (int c = startCol; c < lastCellNum && valueIndex < values.length; c++) {
                    Cell cell = row.getCell(c, Row.MissingCellPolicy.CREATE_NULL_AS_BLANK);
                    cell.setCellType(CellType.STRING);
                    values[valueIndex] = cell.getStringCellValue().trim();
                    valueIndex++;
                }

                Map<String, String> rowData = createRowData(finalHeaders.toArray(new String[0]), values);
                if (rowData != null) {
                    // Check if row has any actual content to avoid empty rows
                    boolean hasContent = rowData.values().stream().anyMatch(v -> v != null && !v.trim().isEmpty());
                    if (hasContent) {
                        jsonList.add(rowData);
                        rowCount++;
                    }
                }
            }
            log.info("Successfully parsed {} rows from Excel file", rowCount);
        }

        return jsonList;
    }
}
