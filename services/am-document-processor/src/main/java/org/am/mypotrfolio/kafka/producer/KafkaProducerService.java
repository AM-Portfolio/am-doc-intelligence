package org.am.mypotrfolio.kafka.producer;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

import org.am.mypotrfolio.kafka.model.PortfolioUpdateEvent;
import org.am.mypotrfolio.kafka.model.TradeUpdateEvent;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.header.internals.RecordHeaders;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import java.util.UUID;
import org.springframework.stereotype.Service;

@Slf4j
@Service
public class KafkaProducerService {

    private final KafkaTemplate<String, Object> kafkaTemplate;

    @Value("${app.kafka.portfolio-topic}")
    private String portfolioTopic;

    @Value("${app.kafka.trade-topic}")
    private String tradeTopic;

    public KafkaProducerService(
            @org.springframework.beans.factory.annotation.Autowired(required = false) KafkaTemplate<String, Object> kafkaTemplate) {
        this.kafkaTemplate = kafkaTemplate;
    }

    public void sendPortfolioUpdate(PortfolioUpdateEvent event) {
        if (kafkaTemplate == null) {
            log.warn("Kafka is disabled. Portfolio update not sent: {}", event);
            return;
        }

        log.info("Sending portfolio update event: {}", event);
        RecordHeaders headers = buildCommonHeaders(
                event.getId(),
                event.getUserId(),
                event.getTimestamp());
        sendKafkaMessage(portfolioTopic, event.getId().toString(), event, headers);
    }

    public void sendTradeUpdate(TradeUpdateEvent event) {
        if (kafkaTemplate == null) {
            log.warn("Kafka is disabled. Trade update not sent: {}", event);
            return;
        }

        log.info("Sending trade update event: {}", event);
        RecordHeaders headers = buildCommonHeaders(
                event.getId(),
                event.getUserId(),
                event.getTimestamp());
        sendKafkaMessage(tradeTopic, event.getId().toString(), event, headers);
    }

    private RecordHeaders buildCommonHeaders(UUID id, String userId, Object timestamp) {
        RecordHeaders headers = new RecordHeaders();
        headers.add("id", id.toString().getBytes());
        headers.add("userId", userId.getBytes());
        headers.add("timestamp", String.valueOf(timestamp).getBytes());
        return headers;
    }

    private void sendKafkaMessage(String topicName, String key, Object event, RecordHeaders headers) {
        ProducerRecord<String, Object> record = new ProducerRecord<>(topicName, null, key, event, headers);
        kafkaTemplate.send(record)
                .whenComplete((result, ex) -> {
                    if (ex == null) {
                        log.info("Message sent successfully to topic: {}, partition: {}, offset: {}",
                                result.getRecordMetadata().topic(),
                                result.getRecordMetadata().partition(),
                                result.getRecordMetadata().offset());
                    } else {
                        log.error("Failed to send message", ex);
                    }
                });
    }

}
