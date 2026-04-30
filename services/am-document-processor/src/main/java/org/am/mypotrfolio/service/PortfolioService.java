package org.am.mypotrfolio.service;

import java.util.List;

import org.am.mypotrfolio.domain.common.DocumentRequest;

import com.am.common.amcommondata.model.asset.equity.EquityModel;
import com.am.common.amcommondata.model.asset.mutualfund.MutualFundModel;

public interface PortfolioService {

    List<EquityModel> processEquityFile(DocumentRequest portfolioRequest);

    List<MutualFundModel> processMutualFundFile(DocumentRequest portfolioRequest);

    default Double getDouble(String value) {
        if (value == null || value.trim().isEmpty()) {
            return 0.0;
        }
        return Double.parseDouble(value.replaceAll(",", ""));
    }

    default Double round(Double value) {
        if (value == null) {
            return 0.0;
        }
        return Math.round(value * 100.0) / 100.0;
    }
}
