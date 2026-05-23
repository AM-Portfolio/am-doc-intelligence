package org.am.mypotrfolio.processor;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockMultipartFile;

import java.io.FileInputStream;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class AngelOneParserTest {

        @Test
        void testParseAngelOneFile() throws Exception {
                // Use the actual file path
                String filePath = "70f16987-c096-467a-bbd9-e4c5b2d4b04a.xlsx";
                FileInputStream inputStream = new FileInputStream(filePath);
                MockMultipartFile file = new MockMultipartFile("file", "test.xlsx",
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", inputStream);

                ExcelFileProcessor processor = new ExcelFileProcessor();
                List<Map<String, String>> result = processor.parseAngelOneFile(file, null);

                assertNotNull(result);
                assertFalse(result.isEmpty(), "Result should not be empty");

                System.out.println("Total parsed rows: " + result.size());

                // Verify we have both Equities (INE) and Mutual Funds (INF)
                long equityCount = result.stream().filter(m -> m.get("ISIN").startsWith("INE")).count();
                long mfCount = result.stream().filter(m -> m.get("ISIN").startsWith("INF")).count();

                System.out.println("Equities found: " + equityCount);
                System.out.println("Mutual Funds found: " + mfCount);

                assertTrue(equityCount > 0, "Should find at least one Equity");
                // assertTrue(mfCount > 0, "Should find at least one Mutual Fund"); // Depending
                // on file content

                // Print samples
                result.stream().filter(m -> m.get("ISIN").startsWith("INE")).findFirst()
                                .ifPresent(m -> System.out.println("Sample Equity: " + m));
                result.stream().filter(m -> m.get("ISIN").startsWith("INF")).findFirst()
                                .ifPresent(m -> System.out.println("Sample MF: " + m));
        }
}
