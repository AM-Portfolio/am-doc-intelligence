package org.am.mypotrfolio.service.splitter;

import com.am.common.amcommondata.model.enums.BrokerType;
import lombok.extern.slf4j.Slf4j;
import org.am.mypotrfolio.domain.common.DocumentRequest;
import org.am.mypotrfolio.domain.common.DocumentType;
import org.am.mypotrfolio.service.detection.DetectionResult;
import org.apache.poi.ss.usermodel.Sheet;
import org.apache.poi.ss.usermodel.Workbook;
import org.apache.poi.ss.usermodel.WorkbookFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.multipart.MultipartFile;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Splits a multi-sheet Excel file into one {@link DocumentRequest} per relevant sheet.
 *
 * <p>Handles two cases:</p>
 * <ol>
 *   <li><b>Angel One COMBINE_PORTFOLIO</b> — an Excel with sheets such as "Equity Holdings"
 *       and "Mutual Fund Holdings". Split into STOCK_PORTFOLIO + MUTUAL_FUND requests.</li>
 *   <li><b>User-aggregated multi-broker Excel</b> — sheet names match broker keywords
 *       (e.g. "Zerodha", "Dhan"). Each sheet becomes an independent STOCK_PORTFOLIO request
 *       with the detected broker type.</li>
 * </ol>
 *
 * <p>If a sheet does not match any known pattern it is skipped with a warning log.</p>
 */
@Slf4j
@Component
public class MultiSheetExcelSplitter implements MultiPortfolioSplitter {

    /** Sheet-name → (BrokerType, DocumentType) mappings for user-aggregated files. */
    private static final Map<String, BrokerType> SHEET_TO_BROKER = Map.of(
            "ZERODHA", BrokerType.ZERODHA,
            "DHAN", BrokerType.DHAN,
            "UPSTOX", BrokerType.UPSTOX,
            "GROWW", BrokerType.GROWW,
            "MSTOCK", BrokerType.MSTOCK,
            "ANGEL", BrokerType.ANGEL_ONE
    );

    /** Angel One specific sheet names. */
    private static final String ANGEL_EQUITY_SHEET = "EQUITY";
    private static final String ANGEL_MF_SHEET = "MUTUAL";

    @Override
    public boolean canSplit(MultipartFile file, DetectionResult detection) {
        if (file == null || file.getOriginalFilename() == null) return false;
        String ext = extension(file.getOriginalFilename());
        if (!ext.equals("xlsx") && !ext.equals("xls")) return false;

        // Angel One combine portfolio is always splittable
        if (detection.getDocumentType() == DocumentType.COMBINE_PORTFOLIO
                && detection.getBrokerType() == BrokerType.ANGEL_ONE) {
            return true;
        }

        // Multi-broker aggregated Excel: check if it has >1 sheet with broker keywords
        try (Workbook wb = WorkbookFactory.create(file.getInputStream())) {
            if (wb.getNumberOfSheets() <= 1) return false;
            int matches = 0;
            for (int i = 0; i < wb.getNumberOfSheets(); i++) {
                if (matchesBrokerSheet(wb.getSheetName(i).toUpperCase())) matches++;
            }
            return matches >= 2;
        } catch (Exception e) {
            log.debug("canSplit check failed: {}", e.getMessage());
            return false;
        }
    }

    @Override
    public List<DocumentRequest> split(MultipartFile file, DetectionResult detection,
                                       String userId, String portfolioId, String password) {
        List<DocumentRequest> requests = new ArrayList<>();
        try (Workbook workbook = password != null && !password.isBlank()
                ? WorkbookFactory.create(file.getInputStream(), password)
                : WorkbookFactory.create(file.getInputStream())) {

            for (int i = 0; i < workbook.getNumberOfSheets(); i++) {
                Sheet sheet = workbook.getSheetAt(i);
                String sheetName = sheet.getSheetName().toUpperCase();

                // Angel One combine portfolio
                if (detection.getBrokerType() == BrokerType.ANGEL_ONE) {
                    if (sheetName.contains(ANGEL_EQUITY_SHEET)) {
                        requests.add(buildRequest(file, workbook, i, BrokerType.ANGEL_ONE,
                                DocumentType.STOCK_PORTFOLIO, userId, portfolioId, password));
                    } else if (sheetName.contains(ANGEL_MF_SHEET)) {
                        requests.add(buildRequest(file, workbook, i, BrokerType.ANGEL_ONE,
                                DocumentType.MUTUAL_FUND, userId, portfolioId, password));
                    }
                    continue;
                }

                // Multi-broker aggregated Excel
                BrokerType broker = resolveSheetBroker(sheetName);
                if (broker != null) {
                    requests.add(buildRequest(file, workbook, i, broker,
                            DocumentType.STOCK_PORTFOLIO, userId, portfolioId, password));
                } else {
                    log.warn("Skipping unrecognised sheet '{}' in file: {}", sheet.getSheetName(),
                            file.getOriginalFilename());
                }
            }
        } catch (Exception e) {
            log.error("Failed to split multi-sheet Excel: {}", file.getOriginalFilename(), e);
            throw new RuntimeException("Failed to split Excel file: " + e.getMessage(), e);
        }

        log.info("Split '{}' into {} sub-requests", file.getOriginalFilename(), requests.size());
        return requests;
    }

    // -------------------------------------------------------------------------
    // Helpers
    // -------------------------------------------------------------------------

    private DocumentRequest buildRequest(MultipartFile original, Workbook workbook, int sheetIndex,
                                         BrokerType brokerType, DocumentType documentType,
                                         String userId, String portfolioId, String password) throws Exception {
        // Materialise a single-sheet workbook so downstream processors see a normal file.
        byte[] sheetBytes = extractSingleSheet(workbook, sheetIndex, original.getOriginalFilename());
        String syntheticName = brokerType.name() + "_" + documentType.name() + "_"
                + original.getOriginalFilename();
        MultipartFile syntheticFile = new InMemoryMultipartFile(
                syntheticName, syntheticName, original.getContentType(),
                new ByteArrayInputStream(sheetBytes).readAllBytes());

        return DocumentRequest.builder()
                .requestId(UUID.randomUUID())
                .file(syntheticFile)
                .brokerType(brokerType)
                .documentType(documentType)
                .userId(userId)
                .portfolioId(portfolioId)
                .password(password)
                .build();
    }

    private byte[] extractSingleSheet(Workbook source, int sheetIndex, String originalName) throws Exception {
        // Create a new workbook containing only the target sheet.
        Workbook single = WorkbookFactory.create(true); // always XSSF for output
        Sheet srcSheet = source.getSheetAt(sheetIndex);
        Sheet destSheet = single.createSheet(srcSheet.getSheetName());

        srcSheet.forEach(row -> {
            var destRow = destSheet.createRow(row.getRowNum());
            row.forEach(cell -> {
                var destCell = destRow.createCell(cell.getColumnIndex());
                switch (cell.getCellType()) {
                    case STRING -> destCell.setCellValue(cell.getStringCellValue());
                    case NUMERIC -> destCell.setCellValue(cell.getNumericCellValue());
                    case BOOLEAN -> destCell.setCellValue(cell.getBooleanCellValue());
                    default -> destCell.setCellValue("");
                }
            });
        });

        ByteArrayOutputStream out = new ByteArrayOutputStream();
        single.write(out);
        single.close();
        return out.toByteArray();
    }

    private boolean matchesBrokerSheet(String sheetNameUpper) {
        return SHEET_TO_BROKER.keySet().stream().anyMatch(sheetNameUpper::contains);
    }

    private BrokerType resolveSheetBroker(String sheetNameUpper) {
        return SHEET_TO_BROKER.entrySet().stream()
                .filter(e -> sheetNameUpper.contains(e.getKey()))
                .map(Map.Entry::getValue)
                .findFirst()
                .orElse(null);
    }

    private String extension(String filename) {
        int dot = filename.lastIndexOf('.');
        return dot >= 0 ? filename.substring(dot + 1).toLowerCase() : "";
    }
}
