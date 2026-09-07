package org.am.mypotrfolio.service;

import org.am.mypotrfolio.kafka.producer.KafkaProducerService;
import org.am.mypotrfolio.model.FileSyncRecord;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.UUID;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verifyNoInteractions;

class MessagingEventServiceTest {

    @Test
    void sendBatchCompletedEventDoesNotPublishPortfolioUpdate() {
        KafkaProducerService kafka = mock(KafkaProducerService.class);
        MessagingEventService service = new MessagingEventService(kafka);

        service.sendBatchCompletedEvent(
                UUID.randomUUID(),
                "user-1",
                List.of(FileSyncRecord.builder().fileName("holdings.xlsx").build()));

        verifyNoInteractions(kafka);
    }
}
