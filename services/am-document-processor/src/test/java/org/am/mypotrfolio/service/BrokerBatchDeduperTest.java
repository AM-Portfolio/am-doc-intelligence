package org.am.mypotrfolio.service;

import com.am.common.amcommondata.model.enums.BrokerType;
import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.List;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class BrokerBatchDeduperTest {

    @Test
    void indicesToSkip_keepsLatestPerBroker() {
        List<BrokerType> brokers = Arrays.asList(
                BrokerType.ZERODHA,
                BrokerType.GROWW,
                BrokerType.ZERODHA);
        Set<Integer> skip = BrokerBatchDeduper.indicesToSkip(brokers);
        assertEquals(Set.of(0), skip);
    }

    @Test
    void indicesToSkip_allUnique_noneSkipped() {
        List<BrokerType> brokers = Arrays.asList(
                BrokerType.ZERODHA,
                BrokerType.GROWW,
                BrokerType.UPSTOX);
        assertTrue(BrokerBatchDeduper.indicesToSkip(brokers).isEmpty());
    }

    @Test
    void indicesToSkip_nullBrokersNeverDuplicate() {
        List<BrokerType> brokers = Arrays.asList(null, null, BrokerType.ZERODHA);
        assertTrue(BrokerBatchDeduper.indicesToSkip(brokers).isEmpty());
    }

    @Test
    void indicesToSkip_threeSame_keepsLastOnly() {
        List<BrokerType> brokers = Arrays.asList(
                BrokerType.DHAN,
                BrokerType.DHAN,
                BrokerType.DHAN);
        assertEquals(Set.of(0, 1), BrokerBatchDeduper.indicesToSkip(brokers));
    }

    @Test
    void skipMessage_includesBrokerAndKeptName() {
        String msg = BrokerBatchDeduper.skipMessage(BrokerType.ZERODHA, "holdings_latest.xlsx");
        assertEquals("Duplicate ZERODHA file; kept holdings_latest.xlsx (latest)", msg);
    }
}
