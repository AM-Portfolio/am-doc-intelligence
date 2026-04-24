package org.am.mypotrfolio.service.mapper;

import java.util.UUID;

import org.am.mypotrfolio.domain.common.NseSecurity;
import org.springframework.stereotype.Component;

import com.am.common.amcommondata.model.security.SecurityKeyModel;
import com.am.common.amcommondata.model.security.SecurityMetadataModel;
import com.am.common.amcommondata.model.security.SecurityModel;

@Component
public class NseSecurityMapper {

    public SecurityModel toSecurityModel(NseSecurity security) {
        if (security == null) {
            return null;
        }

        SecurityModel model = SecurityModel.builder()
                .key(toKeyModel(security))
                .metadata(toMetadataModel(security))
                .build();
        
        // Set ID after building to avoid UUID encoding issues
        model.setId(UUID.randomUUID());
        return model;
    }

    private SecurityKeyModel toKeyModel(NseSecurity security) {
        if (security == null) {
            return null;
        }

        return SecurityKeyModel.builder()
                .symbol(security.getSecurityId())
                .isin(security.getIsin())
                .build();
    }

    private SecurityMetadataModel toMetadataModel(NseSecurity security) {
        if (security == null) {
            return null;
        }

        return SecurityMetadataModel.builder()
                .sector(security.getSectorName())
                .industry(security.getIndustry())
                .build();
    }
}
