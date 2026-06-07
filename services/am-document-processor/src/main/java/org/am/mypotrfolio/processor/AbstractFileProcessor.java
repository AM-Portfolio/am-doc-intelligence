package org.am.mypotrfolio.processor;

import lombok.extern.slf4j.Slf4j;

import org.am.mypotrfolio.domain.common.DocumentRequest;
import org.am.mypotrfolio.domain.common.DocumentType;
import org.springframework.web.multipart.MultipartFile;

import com.am.common.amcommondata.model.enums.BrokerType;

import java.util.*;

@Slf4j
public abstract class AbstractFileProcessor implements FileProcessor {

    @Override
    public List<Map<String, String>> processFile(MultipartFile file, DocumentRequest documentRequest) {
        BrokerType brokerType = documentRequest.getBrokerType();
        log.info("Processing {} file for broker: {}", getFileType(), brokerType);
        try {
            if (brokerType == null) {
                log.debug("Using NSE Security parser");
                return parseNseSecurityFile(file);
            }
            if (brokerType.isZerodha()) {
                log.debug("Using Zerodha parser");
                return (documentRequest.getDocumentType() == DocumentType.TRADE_EQ
                        || documentRequest.getDocumentType() == DocumentType.TRADE_FNO) ? parseZerodhaTradeFile(file)
                                : parseZerodhaFile(file);
            } else if (brokerType.isMStock()) {
                log.debug("Using MStock parser");
                return parseMStockFile(file);
            } else if (brokerType.isDhan()) {
                log.debug("Using Dhan parser");
                return parseDhanFile(file);
            } else if (brokerType.isGrow()) {
                log.debug("Using Grow parser");
                return (documentRequest.getDocumentType() == DocumentType.TRADE_EQ
                        || documentRequest.getDocumentType() == DocumentType.TRADE_MF)
                                ? parseGrowTradeFile(file, documentRequest.getDocumentType())
                                : parseGrowFile(file);
            } else if (brokerType.isAngelOne()) {
                log.debug("Using Angel One parser");
                return parseAngelOneFile(file, documentRequest.getPassword());
            }
            log.debug("Using default Dhan parser");
            return parseDhanFile(file);
        } catch (Exception e) {
            log.error("Error processing {} file: {}", getFileType(), e.getMessage(), e);
            throw new RuntimeException("Failed to process " + getFileType() + " file", e);
        }
    }

    protected abstract List<Map<String, String>> parseZerodhaFile(MultipartFile file) throws Exception;

    protected abstract List<Map<String, String>> parseZerodhaTradeFile(MultipartFile file) throws Exception;

    protected abstract List<Map<String, String>> parseMStockFile(MultipartFile file) throws Exception;

    protected abstract List<Map<String, String>> parseDhanFile(MultipartFile file) throws Exception;

    protected abstract List<Map<String, String>> parseGrowFile(MultipartFile file) throws Exception;

    protected abstract List<Map<String, String>> parseGrowTradeFile(MultipartFile file, DocumentType docType)
            throws Exception;

    protected abstract List<Map<String, String>> parseAngelOneFile(MultipartFile file, String password)
            throws Exception;

    protected abstract List<Map<String, String>> parseNseSecurityFile(MultipartFile file) throws Exception;

    protected Map<String, String> createRowData(String[] headers, String[] values) {
        Map<String, String> row = new LinkedHashMap<>();
        boolean hasData = false;

        for (int i = 0; i < headers.length && i < values.length; i++) {
            String value = values[i] != null ? values[i].trim() : "";
            if (!value.isEmpty()) {
                hasData = true;
            }
            row.put(headers[i].trim(), value);
        }

        return hasData ? row : null;
    }
}
