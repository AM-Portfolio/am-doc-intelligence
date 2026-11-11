package org.am.mypotrfolio.processor;

import org.apache.poi.EncryptedDocumentException;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockMultipartFile;

import java.io.File;
import java.io.FileInputStream;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

class AngelOneParserTest {

    @Test
    void testParseAngelOneFile_requiresPasswordWhenEncrypted() throws Exception {
        File source = new File("70f16987-c096-467a-bbd9-e4c5b2d4b04a.xlsx");
        assumeTrue(source.exists(), "Encrypted Angel One fixture not present");

        try (FileInputStream inputStream = new FileInputStream(source)) {
            MockMultipartFile file = new MockMultipartFile(
                    "file",
                    "test.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    inputStream);

            ExcelFileProcessor processor = new ExcelFileProcessor();
            String password = System.getenv("ANGELONE_TEST_XLSX_PASSWORD");
            if (password == null || password.isBlank()) {
                assertThrows(
                        EncryptedDocumentException.class,
                        () -> processor.parseAngelOneFile(file, null),
                        "Encrypted Angel One workbook must fail closed without a password");
                return;
            }

            List<Map<String, String>> result = processor.parseAngelOneFile(file, password);
            assertNotNull(result);
            assertFalse(result.isEmpty(), "Result should not be empty");
            long equityCount = result.stream()
                    .filter(m -> m.get("ISIN") != null && m.get("ISIN").startsWith("INE"))
                    .count();
            assertTrue(equityCount > 0, "Should find at least one Equity");
        }
    }
}
