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
public class MutualFundAsset {

    @JsonProperty("schemeName")
    @JsonAlias({ "Scheme Name" })
    private String schemeName;

    @JsonProperty("amc")
    @JsonAlias({ "AMC" })
    private String amc;

    @JsonProperty("isin")
    @JsonAlias({ "ISIN", "Isin", "isin" })
    private String isin;

    @JsonProperty("category")
    @JsonAlias({ "Category" })
    private String category;

    @JsonProperty("subCategory")
    @JsonAlias({ "Sub-category" })
    private String subCategory;

    @JsonProperty("folioNo")
    @JsonAlias({ "Folio No." })
    private String folioNo;

    @JsonProperty("units")
    @JsonAlias({ "Units" })
    private String units;

    @JsonProperty("investedValue")
    @JsonAlias({ "Invested Value" })
    private String investedValue;

    @JsonProperty("currentValue")
    @JsonAlias({ "Current Value" })
    private String currentValue;

    @JsonProperty("xirr")
    @JsonAlias({ "XIRR" })
    private String xirr;

}
