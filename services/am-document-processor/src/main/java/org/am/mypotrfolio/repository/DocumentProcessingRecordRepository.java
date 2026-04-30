package org.am.mypotrfolio.repository;

import org.am.mypotrfolio.model.DocumentProcessingRecord;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.UUID;
import java.util.Optional;

@Repository
public interface DocumentProcessingRecordRepository extends MongoRepository<DocumentProcessingRecord, String> {
    Optional<DocumentProcessingRecord> findByProcessId(UUID processId);
}
