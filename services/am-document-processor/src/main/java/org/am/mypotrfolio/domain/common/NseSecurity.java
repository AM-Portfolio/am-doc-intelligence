package org.am.mypotrfolio.domain.common;

import lombok.Data;
import lombok.Builder;
import lombok.NoArgsConstructor;

import org.am.mypotrfolio.domain.common.json.CustomDoubleDeserializer;

import com.fasterxml.jackson.annotation.JsonAlias;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.annotation.JsonDeserialize;

import lombok.AllArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class NseSecurity {

    @JsonProperty("securityId")
    @JsonAlias({"Security Id", "securityId"})
    private String securityId;

    @JsonProperty("securityName")
    @JsonAlias({"Security Name", "securityName"})
    private String securityName;

    @JsonProperty("status")
    @JsonAlias({"Status", "status"})
    private String status;

    @JsonProperty("series")
    @JsonAlias({"Series", "series"})
    private String series;

    @JsonProperty("isin")
    @JsonAlias({"ISIN No", "isin"})
    private String isin;

    @JsonProperty("faceValue")
    @JsonAlias({"Face Value", "faceValue"})
    @JsonDeserialize(using = CustomDoubleDeserializer.class)
    private Double faceValue;

    @JsonProperty("industry")
    @JsonAlias({"Industry", "industry"})
    private String industry;

    @JsonProperty("instrumentType")
    @JsonAlias({"Instrument Type", "instrumentType"})
    private String instrumentType;

    @JsonProperty("sectorName")
    @JsonAlias({"Sector Name", "sectorName"})
    private String sectorName;

    @JsonProperty("industryNewName")
    @JsonAlias({"Industry New Name", "industryNewName"})
    private String industryNewName;

    @JsonProperty("industryGroupName")
    @JsonAlias({"Industry Group Name", "industryGroupName"})
    private String industryGroupName;

    @JsonProperty("industrySubGroupName")
    @JsonAlias({"Industry Sub Group Name", "industrySubGroupName"})
    private String industrySubGroupName;

    @JsonProperty("sectorIndices")
    @JsonAlias({"Sector Indices", "sectorIndices"})
    private String sectorIndices;

    @JsonProperty("thematicIndices")
    @JsonAlias({"Thematic Indices", "thematicIndices"})
    private String thematicIndices;

    @JsonProperty("marketIndices")
    @JsonAlias({"Market Indices", "marketIndices"})
    private String marketIndices;
}   