package org.am.mypotrfolio.service;

import com.am.common.amcommondata.model.enums.BrokerType;

import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Within one multi-doc batch, at most one file per broker is processed.
 * When several files resolve to the same {@link BrokerType}, the <b>latest</b>
 * (highest index) wins and earlier indices are skipped.
 *
 * <p>Null brokers are never treated as duplicates — those entries stay eligible
 * for processing (and typically fail later with a detection error).</p>
 */
public final class BrokerBatchDeduper {

    private BrokerBatchDeduper() {
    }

    /**
     * @param brokersInOrder resolved broker per file index (null allowed)
     * @return skip indices plus the kept (latest) index per broker
     */
    public static DedupResult evaluate(List<BrokerType> brokersInOrder) {
        Map<BrokerType, Integer> lastIndexByBroker = new HashMap<>();
        for (int i = 0; i < brokersInOrder.size(); i++) {
            BrokerType broker = brokersInOrder.get(i);
            if (broker != null) {
                lastIndexByBroker.put(broker, i);
            }
        }

        Set<Integer> skip = new HashSet<>();
        for (int i = 0; i < brokersInOrder.size(); i++) {
            BrokerType broker = brokersInOrder.get(i);
            if (broker != null && lastIndexByBroker.get(broker) != i) {
                skip.add(i);
            }
        }
        return new DedupResult(Collections.unmodifiableSet(skip),
                Collections.unmodifiableMap(lastIndexByBroker));
    }

    /**
     * @param brokersInOrder resolved broker per file index (null allowed)
     * @return indices that must be marked SKIPPED (not processed)
     */
    public static Set<Integer> indicesToSkip(List<BrokerType> brokersInOrder) {
        return evaluate(brokersInOrder).skipIndices();
    }

    public static String skipMessage(BrokerType broker, String keptFileName) {
        String brokerLabel = broker != null ? broker.name() : "UNKNOWN";
        String kept = keptFileName != null && !keptFileName.isBlank() ? keptFileName : "latest file";
        return "Duplicate " + brokerLabel + " file; kept " + kept + " (latest)";
    }

    public record DedupResult(Set<Integer> skipIndices, Map<BrokerType, Integer> keptIndexByBroker) {
    }
}
