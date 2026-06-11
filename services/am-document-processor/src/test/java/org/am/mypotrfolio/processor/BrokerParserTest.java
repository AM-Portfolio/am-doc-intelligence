package org.am.mypotrfolio.processor;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockMultipartFile;

import java.io.File;
import java.io.FileInputStream;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class BrokerParserTest {

    private final ExcelFileProcessor excelProcessor = new ExcelFileProcessor();
    private final CsvFileProcessor csvProcessor = new CsvFileProcessor();

    private MockMultipartFile createMockFile(String relativePath) throws Exception {
        File file = new File(relativePath);
        assertTrue(file.exists(), "File not found: " + file.getAbsolutePath());
        FileInputStream inputStream = new FileInputStream(file);
        
        String contentType = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
        if (relativePath.endsWith(".csv")) {
            contentType = "text/csv";
        }
        
        return new MockMultipartFile("file", file.getName(), contentType, inputStream);
    }

    private void printResults(String testName, List<Map<String, String>> result) {
        System.out.println("==================================================");
        System.out.println("TEST: " + testName);
        System.out.println("Total parsed rows: " + result.size());
        if (!result.isEmpty()) {
            System.out.println("Headers: " + result.get(0).keySet());
            System.out.println("Sample row 1: " + result.get(0));
            if (result.size() > 1) {
                System.out.println("Sample row 2: " + result.get(1));
            }
        } else {
            System.out.println("[!] Warning: Parsed list is empty!");
        }
        System.out.println("==================================================");
    }

    @Test
    void testParseDhanPortfolioEQ() throws Exception {
        MockMultipartFile file = createMockFile("docs/Dhan_Portfolio_EQ_01-05-2026.xlsx");
        List<Map<String, String>> result = excelProcessor.parseDhanFile(file);
        assertNotNull(result);
        assertFalse(result.isEmpty(), "Dhan EQ result should not be empty");
        printResults("Dhan Portfolio EQ", result);
    }

    @Test
    void testParseDhanPortfolioETF() throws Exception {
        MockMultipartFile file = createMockFile("docs/Dhan_Portfolio_ETF_01-05-2026.xlsx");
        List<Map<String, String>> result = excelProcessor.parseDhanFile(file);
        assertNotNull(result);
        assertFalse(result.isEmpty(), "Dhan ETF result should not be empty");
        printResults("Dhan Portfolio ETF", result);
    }

    @Test
    void testParseGrowwHoldings() throws Exception {
        // Test first holdings file
        MockMultipartFile file1 = createMockFile("docs/Stocks_Holdings_Statement_3060484652_2026-01-21_1769102041357.xlsx");
        List<Map<String, String>> result1 = excelProcessor.parseGrowFile(file1);
        assertNotNull(result1);
        assertFalse(result1.isEmpty(), "Groww holdings 1 should not be empty");
        printResults("Groww Holdings 1", result1);

        // Test second holdings file
        MockMultipartFile file2 = createMockFile("docs/Stocks_Holdings_Statement_3060484652_2026-02-07_1770558733163.xlsx");
        List<Map<String, String>> result2 = excelProcessor.parseGrowFile(file2);
        assertNotNull(result2);
        assertFalse(result2.isEmpty(), "Groww holdings 2 should not be empty");
        printResults("Groww Holdings 2", result2);
    }

    @Test
    void testParseGrowwOrders() throws Exception {
        // Groww orders might be parsed as order/trade history. Let's see if we can parse it as Groww file format
        MockMultipartFile file1 = createMockFile("docs/Stocks_Order_History_3060484652_2020-04-01_2026-01-21_1769101861896.xlsx");
        List<Map<String, String>> result1 = excelProcessor.parseGrowFile(file1);
        assertNotNull(result1);
        assertFalse(result1.isEmpty(), "Groww orders 1 should not be empty");
        printResults("Groww Orders 1", result1);

        MockMultipartFile file2 = createMockFile("docs/Stocks_Order_History_3060484652_2020-04-01_2026-02-07_1770557386613.xlsx");
        List<Map<String, String>> result2 = excelProcessor.parseGrowFile(file2);
        assertNotNull(result2);
        assertFalse(result2.isEmpty(), "Groww orders 2 should not be empty");
        printResults("Groww Orders 2", result2);
    }

    @Test
    void testParseZerodhaHoldings() throws Exception {
        MockMultipartFile file = createMockFile("docs/holdings-BKJ665 (2).xlsx");
        List<Map<String, String>> result = excelProcessor.parseZerodhaFile(file);
        assertNotNull(result);
        assertFalse(result.isEmpty(), "Zerodha holdings xlsx should not be empty");
        printResults("Zerodha Holdings XLSX", result);
    }

    @Test
    void testParseZerodhaHoldingsCsv() throws Exception {
        MockMultipartFile file = createMockFile("docs/holdings.csv");
        List<Map<String, String>> result = csvProcessor.parseZerodhaFile(file);
        assertNotNull(result);
        assertFalse(result.isEmpty(), "Zerodha holdings csv should not be empty");
        printResults("Zerodha Holdings CSV", result);
    }

    @Test
    void testParseZerodhaTradebookEQ() throws Exception {
        MockMultipartFile file = createMockFile("docs/tradebook-BKJ665-EQ (1).xlsx");
        List<Map<String, String>> result = excelProcessor.parseZerodhaTradeFile(file);
        assertNotNull(result);
        assertFalse(result.isEmpty(), "Zerodha tradebook EQ should not be empty");
        printResults("Zerodha Tradebook EQ", result);
    }

    @Test
    void testParseZerodhaTradebookEQ2() throws Exception {
        MockMultipartFile file = createMockFile("docs/tradebook-BKJ665-EQ_2.xlsx");
        List<Map<String, String>> result = excelProcessor.parseZerodhaTradeFile(file);
        assertNotNull(result);
        assertFalse(result.isEmpty(), "Zerodha tradebook EQ 2 should not be empty");
        printResults("Zerodha Tradebook EQ 2", result);
        
        // Assert that extracted columns contain new fields like Order ID
        Map<String, String> firstRow = result.get(0);
        assertTrue(firstRow.containsKey("Order ID"), "Parsed data should contain Order ID");
        assertTrue(firstRow.containsKey("Trade ID"), "Parsed data should contain Trade ID");
        assertTrue(firstRow.containsKey("ISIN"), "Parsed data should contain ISIN");
    }

    @Test
    void testParseZerodhaTradebookFO() throws Exception {
        MockMultipartFile file = createMockFile("docs/tradebook-BKJ665-FO.xlsx");
        List<Map<String, String>> result = excelProcessor.parseZerodhaTradeFile(file);
        assertNotNull(result);
        assertFalse(result.isEmpty(), "Zerodha tradebook FO should not be empty");
        printResults("Zerodha Tradebook FO", result);
    }

    @Test
    void testParseMStockTradeHistory() throws Exception {
        MockMultipartFile file = createMockFile("docs/trade_history2024-06-21_2026-02-11_1770823206679.xlsx");
        List<Map<String, String>> result = excelProcessor.parseMStockFile(file);
        assertNotNull(result);
        assertFalse(result.isEmpty(), "MStock trade history should not be empty");
        printResults("MStock Trade History", result);
    }

    @Test
    void testParseMStockPortfolioNew() throws Exception {
        MockMultipartFile file = createMockFile("docs/Portfolio_report_1781113687706.xlsx");
        List<Map<String, String>> result = excelProcessor.parseMStockFile(file);
        assertNotNull(result);
        assertFalse(result.isEmpty(), "MStock portfolio should not be empty");
        printResults("MStock Portfolio New", result);

        // Verify some properties from MStock Portfolio report
        Map<String, String> row = result.get(0);
        assertTrue(row.containsKey("Symbol"), "Parsed row should contain Symbol");
        assertTrue(row.containsKey("Quantity"), "Parsed row should contain Quantity");
        assertTrue(row.containsKey("Average Price"), "Parsed row should contain Average Price");
        assertEquals("APLLTD", row.get("Symbol"));
        assertEquals("3", row.get("Quantity"));
        assertEquals("1145.55", row.get("Average Price"));
    }

    @Test
    void testParseMStockTradeHistoryNew() throws Exception {
        MockMultipartFile file = createMockFile("docs/trade_history2025-04-01_2026-03-31_1781113567782.xlsx");
        List<Map<String, String>> result = excelProcessor.parseMStockFile(file);
        assertNotNull(result);
        assertFalse(result.isEmpty(), "MStock trade history should not be empty");
        printResults("MStock Trade History New", result);

        // Verify first row contents from MStock Trade History
        Map<String, String> row = result.get(0);
        assertEquals("BAJAJ-AUTO", row.get("Symbol"));
        assertEquals("Sell", row.get("Type"));
        assertEquals("5", row.get("Quantity"));
        assertEquals("8765.00", row.get("Price"));
        assertEquals("2025-08-19", row.get("Trade Date"));
    }

    @Test
    void testParseNewGrowwStocks() throws Exception {
        MockMultipartFile file = createMockFile("docs/Stocks_Holdings_Statement_3060484652_2026-05-23.xlsx");
        List<Map<String, String>> result = excelProcessor.parseGrowFile(file);
        assertNotNull(result);
        assertFalse(result.isEmpty(), "New Groww stocks should not be empty");
        printResults("New Groww Stocks", result);
        assertTrue(result.get(0).containsKey("Average Price"), "Should map 'Average buy price' to 'Average Price'");
    }

    @Test
    void testParseNewGrowwMutualFunds() throws Exception {
        MockMultipartFile file = createMockFile("docs/Holdings_Statement_2026-05-24.xlsx");
        List<Map<String, String>> result = excelProcessor.parseGrowFile(file);
        assertNotNull(result);
        assertFalse(result.isEmpty(), "New Groww mutual funds should not be empty");
        printResults("New Groww Mutual Funds", result);
    }

    @Test
    void testParseGrowwStockTradeHistory() throws Exception {
        MockMultipartFile file = createMockFile("docs/Stocks_Order_History_3060484652_2026-04-01_2026-06-06-1.xlsx");
        List<Map<String, String>> result = excelProcessor.parseGrowTradeFile(file, org.am.mypotrfolio.domain.common.DocumentType.TRADE_EQ);
        assertNotNull(result);
        assertFalse(result.isEmpty(), "Groww stock trade history should not be empty");
        printResults("Groww Stock Trade History", result);

        Map<String, String> row = result.get(0);
        assertTrue(row.containsKey("Symbol"), "Parsed row should contain Symbol");
        assertTrue(row.containsKey("Price"), "Parsed row should contain Price");
        assertTrue(row.containsKey("Trade Date"), "Parsed row should contain Trade Date");
        assertEquals("2026-04-08", row.get("Trade Date"), "Parsed trade date should match execution date");
    }

    @Test
    void testParseGrowwMfTradeHistory() throws Exception {
        MockMultipartFile file = createMockFile("docs/Mutual_Funds_Order_History_2025_2026.xlsx");
        // Mutual_Funds_Order_History_2025_2026.xlsx contains "NO TRANSACTIONS FOUND"
        // So the returned list will be empty, which is expected behavior
        List<Map<String, String>> result = excelProcessor.parseGrowTradeFile(file, org.am.mypotrfolio.domain.common.DocumentType.TRADE_MF);
        assertNotNull(result);
        assertTrue(result.isEmpty(), "Groww MF trade history should be empty for a file with no transactions");
        printResults("Groww MF Trade History (Empty)", result);
    }

    @Test
    void testParseAngelOneTradeHistory() throws Exception {
        MockMultipartFile file = createMockFile("docs/a1338c6d-d30e-4595-b9f4-bdb4bd2fec33.xlsx");
        List<Map<String, String>> result = excelProcessor.parseAngelOneFile(file, null);
        assertNotNull(result);
        assertFalse(result.isEmpty(), "Angel One trade history should not be empty");
        printResults("Angel One Trade History", result);

        Map<String, String> row = result.get(0);
        assertTrue(row.containsKey("Symbol"), "Parsed row should contain Symbol");
        assertTrue(row.containsKey("Price"), "Parsed row should contain Price");
        assertTrue(row.containsKey("Trade Date"), "Parsed row should contain Trade Date");
        assertTrue(row.containsKey("Order ID"), "Parsed row should contain Order ID");
        assertTrue(row.containsKey("Trade ID"), "Parsed row should contain Trade ID");
        assertTrue(row.containsKey("Exchange"), "Parsed row should contain Exchange");
        
        // Assert specific row contents from the test file:
        // 'BHARTI AIRTEL LIMITE', 'Sell', '', 1687.9, 3
        assertEquals("BHARTI AIRTEL LIMITE", row.get("Symbol"));
        assertEquals("Sell", row.get("Type"));
        assertEquals("1687.9", row.get("Price"));
        assertEquals("3.0", row.get("Quantity"));
        assertEquals("2025-02-10", row.get("Trade Date"));
        assertEquals("1000000018181238", row.get("Order ID"));
        assertEquals("2338290", row.get("Trade ID"));
        assertEquals("NSE", row.get("Exchange"));
    }
}
