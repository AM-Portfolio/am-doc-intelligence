package org.am.mypotrfolio.utils;

import lombok.RequiredArgsConstructor;
import lombok.SneakyThrows;

import org.apache.poi.ss.usermodel.Cell;
import org.apache.poi.ss.usermodel.CellType;
import org.apache.poi.ss.usermodel.Row;
import org.apache.poi.ss.usermodel.Sheet;
import org.apache.poi.ss.usermodel.Workbook;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.springframework.stereotype.Component;
import org.springframework.web.multipart.MultipartFile;

import java.io.InputStream;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Component
@RequiredArgsConstructor
public class NseFileBuilder {


    public  List<Map<String, String>> parseExcel(MultipartFile file, String brokerType) throws Exception {
        if(brokerType.equalsIgnoreCase("Zerodha")) {
            return parseZerodhaExcel(file);
        } else if(brokerType.equalsIgnoreCase("MStock")) {
            return parseMStockExcel(file);
        } else if(brokerType.equalsIgnoreCase("Dhan")) {
            return parseDhanExcel(file);
        }
        return parseDhanExcel(file);
    }

    @SneakyThrows
    private List<Map<String, String>> parseMStockExcel(MultipartFile file) {
        List<Map<String, String>> jsonList = new ArrayList<>();

        try (InputStream inputStream = file.getInputStream();
             Workbook workbook = new XSSFWorkbook(inputStream)) {

            Sheet sheet = workbook.getSheetAt(0); // Read first sheet
            Iterator<Row> rowIterator = sheet.iterator();
            
            List<String> headers = new ArrayList<>();

            while (rowIterator.hasNext()) {
                Row row = rowIterator.next();
                Map<String, String> rowData = new LinkedHashMap<>();
                for (Cell cell : row) {
                    cell.setCellType(CellType.STRING); // Convert all cells to string
                    
                    if (row.getRowNum() == 0 ) { // Read header row
                        headers.add(cell.getStringCellValue().trim());
                    } else { // Read data rows
                        if (cell.getColumnIndex() < headers.size()-2) {
                            rowData.put(headers.get(cell.getColumnIndex()), cell.getStringCellValue());
                        }
                    }
                }

                if (!rowData.isEmpty()) {
                    jsonList.add(rowData);
                }
            }
        }

        return jsonList;
    }

    @SneakyThrows
    private List<Map<String, String>> parseZerodhaExcel(MultipartFile file) {
        List<Map<String, String>> jsonList = new ArrayList<>();

        try (InputStream inputStream = file.getInputStream();
             Workbook workbook = new XSSFWorkbook(inputStream)) {

            Sheet sheet = workbook.getSheetAt(0); // Read first sheet
            Iterator<Row> rowIterator = sheet.iterator();
            
            List<String> headers = new ArrayList<>();

            while (rowIterator.hasNext()) {
                Row row = rowIterator.next();
                if (row.getRowNum() >=0 && row.getRowNum()<22) continue;
                Map<String, String> rowData = new LinkedHashMap<>();
                for (Cell cell : row) {
                    cell.setCellType(CellType.STRING); // Convert all cells to string
                     // && !StringUtils.isEmpty(cell.getStringCellValue().trim())
                    if (row.getRowNum() == 22 ) { // Read header row
                        headers.add(cell.getStringCellValue().trim());
                    } else { // Read data rows
                        if (cell.getColumnIndex() < headers.size()-1) {
                            rowData.put(headers.get(cell.getColumnIndex() -1 ), cell.getStringCellValue());
                        }
                    }
                }

                if (!rowData.isEmpty()) {
                    jsonList.add(rowData);
                }
            }
        }

        return jsonList;
    }

    @SneakyThrows
    private List<Map<String, String>> parseDhanExcel(MultipartFile file) {
        List<Map<String, String>> jsonList = new ArrayList<>();

        try (InputStream inputStream = file.getInputStream();
             Workbook workbook = new XSSFWorkbook(inputStream)) {

            Sheet sheet = workbook.getSheetAt(0); // Read first sheet
            Iterator<Row> rowIterator = sheet.iterator();
            
            List<String> headers = new ArrayList<>();

            while (rowIterator.hasNext()) {
                Row row = rowIterator.next();
                Map<String, String> rowData = new LinkedHashMap<>();
                
                for (Cell cell : row) {
                    cell.setCellType(CellType.STRING); // Convert all cells to string

                    if (row.getRowNum() == 0) { // Read header row
                        headers.add(cell.getStringCellValue().trim());
                    } else { // Read data rows
                        if (cell.getColumnIndex() < headers.size()) {
                            rowData.put(headers.get(cell.getColumnIndex()), cell.getStringCellValue());
                        }
                    }
                }

                if (!rowData.isEmpty()) {
                    jsonList.add(rowData);
                }
            }
        }

        return jsonList;
    }

}
