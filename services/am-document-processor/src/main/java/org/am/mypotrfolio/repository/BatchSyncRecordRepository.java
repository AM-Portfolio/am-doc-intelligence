package org.am.mypotrfolio.repository;

import org.am.mypotrfolio.model.BatchSyncRecord;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

/**
 * MongoDB repository for {@link BatchSyncRecord}.
 */
@Repository
public interface BatchSyncRecordRepository extends MongoRepository<BatchSyncRecord, String> {

    Optional<BatchSyncRecord> findByBatchIdAndUserId(String batchId, String userId);

    List<BatchSyncRecord> findByUserIdOrderByCreatedAtDesc(String userId);
}
