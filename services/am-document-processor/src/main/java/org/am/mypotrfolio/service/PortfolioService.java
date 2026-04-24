package org.am.mypotrfolio.service;

import java.util.List;

import org.am.mypotrfolio.domain.common.DocumentRequest;

import com.am.common.amcommondata.model.asset.equity.EquityModel;
import com.am.common.amcommondata.model.asset.mutualfund.MutualFundModel;

public interface PortfolioService {

    List<EquityModel> processEquityFile(DocumentRequest portfolioRequest);

    List<MutualFundModel> processMutualFundFile(DocumentRequest portfolioRequest);

    default Double getDouble(String value) {
        return Double.parseDouble(value.replaceAll(",", ""));
    }
}
