package org.am.mypotrfolio.service.detection;

import com.am.common.amcommondata.model.enums.BrokerType;
import lombok.extern.slf4j.Slf4j;
import org.am.mypotrfolio.domain.common.DocumentType;
import org.apache.poi.EncryptedDocumentException;
import org.apache.poi.ss.usermodel.*;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.multipart.MultipartFile;

import java.io.InputStream;
import java.util.Set;

/**
 * Content-based broker detection for Excel files (xlsx / xls).
 *
 * <p>Inspects sheet names and the first few header cells to fingerprint the broker.
 * Confidence is higher (85) than filename-only because content is harder to fake
 * accidentally, and survives renaming.</p>
 *
 * <p>Detection signatures:</p>
 * <ul>
 *   <li>Upstox — cell[0][0] contains "UPSTOX" or sheet name contains "Holdings"</li>
 *   <li>Zerodha — sheet name "Portfolio" + header "Symbol"/"Instrument"</li>
 *   <li>Angel One — workbook is password-protected (encrypted)</li>
 *   <li>Dhan — header "Buy Avg. Cost Price" present</li>
 *   <li>Groww — header "Current Value (INR)" or "Gain/Loss"</li>
 *   <li>MStock — header "Avg. Price" + "Scripcode"</li>
 * </ul>
 */
@Slf4j
@Component
@Order(5)
public class ExcelContentBrokerDetectionStrategy implements BrokerDetectionStrategy {

    private static final Set<String> EXCEL_EXTENSIONS = Set.of("xlsx", "xls");
    private static final int CONTENT_CONFIDENCE = 85;

    @Override
    public boolean supports(String fileExtension) {
        return fileExtension != null && EXCEL_EXTENSIONS.contains(fileExtension.toLowerCase());
    }

    @Override
    public int confidence(MultipartFile file, String passwordHint) {
        if (file == null) return 0;
        try {
            return detect(file, passwordHint).isKnown() ? CONTENT_CONFIDENCE : 0;
        } catch (Exception e) {
            log.debug("ExcelContent confidence check failed for {}: {}", file.getOriginalFilename(), e.getMessage());
            return 0;
        }
    }

    @Override
    public DetectionResult detect(MultipartFile file, String passwordHint) {
        try {
            // First try to open — if the workbook is encrypted and no password is given,
            // it is likely Angel One.
            InputStream stream = file.getInputStream();
            Workbook workbook;
            try {
                workbook = passwordHint != null && !passwordHint.isBlank()
                        ? WorkbookFactory.create(stream, passwordHint)
                        : WorkbookFactory.create(stream);
            } catch (EncryptedDocumentException e) {
                log.debug("Workbook encrypted (no/wrong password) — likely Angel One: {}", file.getOriginalFilename());
                return new DetectionResult(BrokerType.ANGEL_ONE, DocumentType.COMBINE_PORTFOLIO, CONTENT_CONFIDENCE);
            }

            try (workbook) {
                return inspectWorkbook(workbook, file.getOriginalFilename());
            }
        } catch (Exception e) {
            log.debug("Excel content detection failed for {}: {}", file.getOriginalFilename(), e.getMessage());
            return DetectionResult.unknown();
        }
    }

    private DetectionResult inspectWorkbook(Workbook workbook, String filename) {
        int sheetCount = workbook.getNumberOfSheets();

        // Collect all sheet names for multi-sheet fingerprinting
        StringBuilder allSheetNames = new StringBuilder();
        for (int i = 0; i < sheetCount; i++) {
            allSheetNames.append(workbook.getSheetName(i).toUpperCase()).append(" ");
        }
        String sheetNamesStr = allSheetNames.toString();

        // Zerodha: has "Equity" + "Mutual Funds" + "Combined" sheets (tax/holdings export)
        if (sheetNamesStr.contains("EQUITY") && sheetNamesStr.contains("MUTUAL") && sheetNamesStr.contains("COMBINED")) {
            return new DetectionResult(BrokerType.ZERODHA, DocumentType.COMBINE_PORTFOLIO, CONTENT_CONFIDENCE);
        }

        // Upstox: sheet name contains the broker name. Do not match generic "Holdings_"
        // prefixes — Groww and other brokers also use that filename/sheet pattern.
        if (sheetNamesStr.contains("UPSTOX")) {
            return new DetectionResult(BrokerType.UPSTOX, DocumentType.STOCK_PORTFOLIO, CONTENT_CONFIDENCE);
        }

        // Groww: has "All", "T1", "Demat", "Pledged" sheets
        if (sheetNamesStr.contains("DEMAT") && sheetNamesStr.contains("PLEDGED")) {
            return new DetectionResult(BrokerType.GROWW, DocumentType.STOCK_PORTFOLIO, CONTENT_CONFIDENCE);
        }

        // Angel One: Equity + Mutual Fund sheets (combined portfolio)
        if (sheetNamesStr.contains("EQUITY") && sheetNamesStr.contains("MUTUAL")) {
            return new DetectionResult(BrokerType.ANGEL_ONE, DocumentType.COMBINE_PORTFOLIO, CONTENT_CONFIDENCE);
        }

        // Inspect first sheet headers
        Sheet sheet = workbook.getSheetAt(0);
        if (sheet == null) return DetectionResult.unknown();

        // Cell[0][0] content
        Row firstRow = sheet.getRow(0);
        if (firstRow != null) {
            String cell00 = cellString(firstRow.getCell(0)).toUpperCase();
            if (cell00.contains("UPSTOX")) {
                return new DetectionResult(BrokerType.UPSTOX, DocumentType.STOCK_PORTFOLIO, CONTENT_CONFIDENCE);
            }
        }

        // Scan first 25 rows for header fingerprints (Zerodha guide text appears deep in the sheet)
        String headers = extractHeaders(sheet, 25).toUpperCase();

        // Zerodha: has guide text in cell content
        if (headers.contains("ZERODHA") || headers.contains("VIEW ZERODHA")) {
            // Check if it's equity-only or combined
            boolean hasEquity = headers.contains("SYMBOL") && headers.contains("ISIN");
            DocumentType dt = hasEquity ? DocumentType.STOCK_PORTFOLIO : DocumentType.COMBINE_PORTFOLIO;
            return new DetectionResult(BrokerType.ZERODHA, dt, CONTENT_CONFIDENCE);
        }
        if (headers.contains("BUY AVG. COST PRICE") || headers.contains("TRADING SYMBOL")) {
            return new DetectionResult(BrokerType.DHAN, DocumentType.STOCK_PORTFOLIO, CONTENT_CONFIDENCE);
        }
        if (headers.contains("SCRIPCODE") && headers.contains("AVG. PRICE")) {
            return new DetectionResult(BrokerType.MSTOCK, DocumentType.STOCK_PORTFOLIO, CONTENT_CONFIDENCE);
        }
        if (headers.contains("CURRENT VALUE (INR)") || headers.contains("GAIN/LOSS")) {
            DocumentType dt = headers.contains("FOLIO") ? DocumentType.MUTUAL_FUND : DocumentType.STOCK_PORTFOLIO;
            return new DetectionResult(BrokerType.GROWW, dt, CONTENT_CONFIDENCE);
        }
        // Groww Demat: Symbol, Category, Net Qty, Avg. Price pattern
        if (headers.contains("NET QTY") && headers.contains("AVG. PRICE") && headers.contains("CATEGORY")) {
            return new DetectionResult(BrokerType.GROWW, DocumentType.STOCK_PORTFOLIO, CONTENT_CONFIDENCE);
        }
        // Zerodha holdings: Symbol + ISIN + Average Price (no "ZERODHA" text in sheet)
        if (headers.contains("SYMBOL") && headers.contains("ISIN") && headers.contains("AVERAGE PRICE")) {
            return new DetectionResult(BrokerType.ZERODHA, DocumentType.STOCK_PORTFOLIO, CONTENT_CONFIDENCE);
        }

        return DetectionResult.unknown();
    }

    private String extractHeaders(Sheet sheet, int maxRows) {
        StringBuilder sb = new StringBuilder();
        for (int r = 0; r <= Math.min(maxRows, sheet.getLastRowNum()); r++) {
            Row row = sheet.getRow(r);
            if (row == null) continue;
            for (int c = 0; c < row.getLastCellNum(); c++) {
                sb.append(cellString(row.getCell(c))).append(" ");
            }
        }
        return sb.toString();
    }

    private String cellString(Cell cell) {
        if (cell == null) return "";
        return switch (cell.getCellType()) {
            case STRING -> cell.getStringCellValue();
            case NUMERIC -> String.valueOf((long) cell.getNumericCellValue());
            default -> "";
        };
    }
}
