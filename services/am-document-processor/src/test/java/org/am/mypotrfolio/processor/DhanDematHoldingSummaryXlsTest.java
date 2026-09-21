package org.am.mypotrfolio.processor;

import com.am.common.amcommondata.model.enums.BrokerType;
import org.am.mypotrfolio.domain.common.DocumentType;
import org.am.mypotrfolio.service.detection.DetectionResult;
import org.am.mypotrfolio.service.detection.ExcelContentBrokerDetectionStrategy;
import org.am.mypotrfolio.service.detection.FilenameBrokerDetectionStrategy;
import org.apache.poi.hssf.usermodel.HSSFWorkbook;
import org.apache.poi.ss.usermodel.Row;
import org.apache.poi.ss.usermodel.Sheet;
import org.apache.poi.ss.usermodel.Workbook;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockMultipartFile;

import java.io.ByteArrayOutputStream;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Regression for classic OLE2 Dhan Demat Holding Summary (.xls):
 * XSSF-only open used to throw OLE2NotOfficeXmlFileException; demat headers
 * (Security Name / Free Holding) must parse and Auto-detect as DHAN.
 */
class DhanDematHoldingSummaryXlsTest {

    private final ExcelFileProcessor excelProcessor = new ExcelFileProcessor();
    private final FilenameBrokerDetectionStrategy filenameDetect = new FilenameBrokerDetectionStrategy();
    private final ExcelContentBrokerDetectionStrategy contentDetect = new ExcelContentBrokerDetectionStrategy();

    @Test
    void filenameDetectsDhanFromDematHoldingSummary() {
        MockMultipartFile file = new MockMultipartFile(
                "file",
                "HYTJ65377G_Demat_Holding_Summary.xls",
                "application/vnd.ms-excel",
                new byte[] {1, 2, 3});
        DetectionResult result = filenameDetect.detect(file, null);
        assertTrue(result.isKnown());
        assertEquals(BrokerType.DHAN, result.getBrokerType());
        assertEquals(DocumentType.STOCK_PORTFOLIO, result.getDocumentType());
    }

    @Test
    void contentAndParseDematHoldingSummaryXls() throws Exception {
        byte[] xls = buildDematHoldingSummaryXls();
        assertEquals(0xd0, xls[0] & 0xff, "fixture must be OLE2/HSSF");
        assertEquals(0xcf, xls[1] & 0xff);

        MockMultipartFile file = new MockMultipartFile(
                "file",
                "HYTJ65377G_Demat_Holding_Summary.xls",
                "application/vnd.ms-excel",
                xls);

        DetectionResult detected = contentDetect.detect(file, null);
        assertTrue(detected.isKnown(), "content detect should recognize demat layout");
        assertEquals(BrokerType.DHAN, detected.getBrokerType());
        assertEquals(DocumentType.STOCK_PORTFOLIO, detected.getDocumentType());

        List<Map<String, String>> rows = excelProcessor.parseDhanFile(file);
        assertFalse(rows.isEmpty(), "parsed holdings must not be empty");
        Map<String, String> first = rows.get(0);
        assertEquals("Adani Energy Solutions", first.get("Scrip Name"));
        assertTrue(first.containsKey("Quantity"), "Free Holding should map to Quantity");
        assertEquals("18.0", first.get("Quantity"));
        assertEquals("INE931S01010", first.get("ISIN Code"));
    }

    private static byte[] buildDematHoldingSummaryXls() throws Exception {
        try (Workbook wb = new HSSFWorkbook(); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            Sheet sheet = wb.createSheet("Demat Holding Summary");
            // Title / padding rows 0-7
            sheet.createRow(0).createCell(2).setCellValue("Demat Holding Summary");
            for (int r = 1; r < 8; r++) {
                sheet.createRow(r);
            }
            Row header = sheet.createRow(8);
            String[] cols = {
                    "Sr.", "Security Type", "ISIN", "Security Name",
                    "Free Holding", "Locked In", "Safe Keep", "MTF Pledge", "Margin Pledge"
            };
            for (int c = 0; c < cols.length; c++) {
                header.createCell(c).setCellValue(cols[c]);
            }
            Row row1 = sheet.createRow(9);
            row1.createCell(0).setCellValue(1);
            row1.createCell(1).setCellValue("listed");
            row1.createCell(2).setCellValue("INE931S01010");
            row1.createCell(3).setCellValue("Adani Energy Solutions");
            row1.createCell(4).setCellValue(18);
            row1.createCell(5).setCellValue(0);
            row1.createCell(6).setCellValue(0);
            row1.createCell(7).setCellValue(0);
            row1.createCell(8).setCellValue(0);

            Row row2 = sheet.createRow(10);
            row2.createCell(0).setCellValue(2);
            row2.createCell(1).setCellValue("listed");
            row2.createCell(2).setCellValue("INE160A01022");
            row2.createCell(3).setCellValue("Punjab National Bank");
            row2.createCell(4).setCellValue(550);
            row2.createCell(5).setCellValue(0);
            row2.createCell(6).setCellValue(0);
            row2.createCell(7).setCellValue(0);
            row2.createCell(8).setCellValue(0);

            wb.write(out);
            return out.toByteArray();
        }
    }
}
