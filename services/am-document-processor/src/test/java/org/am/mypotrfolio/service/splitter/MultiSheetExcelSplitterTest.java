package org.am.mypotrfolio.service.splitter;

import com.am.common.amcommondata.model.enums.BrokerType;
import org.am.mypotrfolio.domain.common.DocumentRequest;
import org.am.mypotrfolio.domain.common.DocumentType;
import org.am.mypotrfolio.service.detection.DetectionResult;
import org.apache.poi.ss.usermodel.Row;
import org.apache.poi.ss.usermodel.Sheet;
import org.apache.poi.ss.usermodel.Workbook;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockMultipartFile;

import java.io.ByteArrayOutputStream;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class MultiSheetExcelSplitterTest {

    private final MultiSheetExcelSplitter splitter = new MultiSheetExcelSplitter();

    @Test
    void canSplitAngelOneCombinePortfolio() throws Exception {
        MockMultipartFile file = workbook("angel.xlsx", "Equity Holdings", "Mutual Fund Holdings");
        DetectionResult detection = new DetectionResult(
                BrokerType.ANGEL_ONE, DocumentType.COMBINE_PORTFOLIO, 85);
        assertTrue(splitter.canSplit(file, detection));
    }

    @Test
    void splitsAngelOneIntoEquityAndMutualFundRequests() throws Exception {
        MockMultipartFile file = workbook("angel.xlsx", "Equity Holdings", "Mutual Fund Holdings");
        DetectionResult detection = new DetectionResult(
                BrokerType.ANGEL_ONE, DocumentType.COMBINE_PORTFOLIO, 85);

        List<DocumentRequest> requests = splitter.split(file, detection, "user-1", "My Angel", null);

        assertEquals(2, requests.size());
        assertEquals(BrokerType.ANGEL_ONE, requests.get(0).getBrokerType());
        assertEquals(DocumentType.STOCK_PORTFOLIO, requests.get(0).getDocumentType());
        assertEquals(DocumentType.MUTUAL_FUND, requests.get(1).getDocumentType());
        assertEquals("My Angel", requests.get(0).getPortfolioId());
        assertEquals("My Angel", requests.get(1).getPortfolioId());
    }

    @Test
    void canSplitMultiBrokerAggregatedExcel() throws Exception {
        MockMultipartFile file = workbook("combined.xlsx", "Zerodha", "Dhan");
        DetectionResult detection = new DetectionResult(null, DocumentType.STOCK_PORTFOLIO, 60);
        assertTrue(splitter.canSplit(file, detection));
    }

    @Test
    void doesNotSplitSingleSheetExcel() throws Exception {
        MockMultipartFile file = workbook("single.xlsx", "Holdings");
        DetectionResult detection = new DetectionResult(
                BrokerType.ZERODHA, DocumentType.STOCK_PORTFOLIO, 85);
        assertFalse(splitter.canSplit(file, detection));
    }

    private static MockMultipartFile workbook(String filename, String... sheetNames) throws Exception {
        try (Workbook wb = new XSSFWorkbook(); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            for (String name : sheetNames) {
                Sheet sheet = wb.createSheet(name);
                Row row = sheet.createRow(0);
                row.createCell(0).setCellValue("Symbol");
                row.createCell(1).setCellValue("Qty");
            }
            wb.write(out);
            return new MockMultipartFile(
                    "file",
                    filename,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    out.toByteArray());
        }
    }
}
