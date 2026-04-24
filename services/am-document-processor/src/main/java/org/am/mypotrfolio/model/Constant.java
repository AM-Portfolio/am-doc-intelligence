package org.am.mypotrfolio.model;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

public class Constant {
    public static final String EXCEL_SHEET_NAME = "Company";
    public static final String ATTACHMENT_FILENAME_COMPANY_TEMPLATE_XLSX = "attachment; filename=";
    public static final String EXCEL_FILENAME = "Company_" + LocalDateTime.now().format(DateTimeFormatter
            .ofPattern("yyyy-MM-dd_HHmmss")) + ".xlsx";

    public static final String EXCEL_PORTFOLIO_FILENAME = "9AMPortfolio_" + LocalDateTime.now().format(DateTimeFormatter
            .ofPattern("yyyy-MM-dd_HHmmss")) + ".xlsx";

    public static final String AMPORTFOLIO_FILE = "portfolio.xlsx";
    public static final String COMPANY_FILE = "company.xlsx";
    public static final String EXCEL_PORTFOLIO_SHEET_NAME = "Portfolio";

}
