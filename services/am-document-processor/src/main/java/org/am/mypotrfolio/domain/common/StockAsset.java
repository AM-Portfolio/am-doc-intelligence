package org.am.mypotrfolio.domain.common;

import com.fasterxml.jackson.annotation.JsonAlias;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class StockAsset {

    @JsonProperty("Name")
    @JsonAlias({ "Name", "prop1", "company_name", "Company Name", "Stock Name", "Stock name", "Scrip Name", "Scrip name" })
    private String name;

    @JsonProperty("ISIN")
    @JsonAlias({ "isin", "ISIN", "isin_code", "ISIN Code" })
    private String isin;

    @JsonProperty("Symbol")
    @JsonAlias({ "Symbol", "prop1", "Scrip Name" })
    private String symbol;

    @JsonProperty("Quantity")
    @JsonAlias({ "Quantity", "Quantity Available", "current_bal", "Balance", "Qty", "Net Qty" })
    private String quantity;

    @JsonProperty("Average Price")
    @JsonAlias({ "Avg. Cost", "Avg Price", "Average Price", "rate", "Avg. Price" })
    private String avgPrice;

    @JsonProperty("Investment")
    @JsonAlias({ "Invested Value", "Investment", "value", "Value", "Invested" })
    private String investmentValue;

}
