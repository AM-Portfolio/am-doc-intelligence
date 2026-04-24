// package org.am.mypotrfolio.kafka.consumer;

// import lombok.extern.slf4j.Slf4j;

// import org.springframework.kafka.annotation.KafkaListener;
// import org.springframework.stereotype.Service;

// @Slf4j
// @Service
// public class KafkaConsumerService {

//     @KafkaListener(topics = "${app.kafka.topic}", groupId = "${spring.kafka.consumer.group-id}")
//     public void consume(Message message) {
//         log.info("Received message: {}", message);
//         // Add your message processing logic here
//     }
// }
