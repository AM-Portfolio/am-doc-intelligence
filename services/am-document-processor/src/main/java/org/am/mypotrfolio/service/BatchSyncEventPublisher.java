package org.am.mypotrfolio.service;

import lombok.extern.slf4j.Slf4j;
import org.am.mypotrfolio.model.FileSyncStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * Manages Server-Sent Event (SSE) emitters for batch sync progress streaming.
 *
 * <p>The SSE endpoint ({@code GET /v1/documents/sync/{batchId}/stream}) registers
 * an emitter here. When a document processor completes or fails a file, it calls
 * {@link #emit(UUID, FileSyncStatus)} which pushes the update to all connected
 * clients for that batch. This gives the UI live per-file progress without polling.</p>
 *
 * <p>Thread-safety: emitters are stored in a {@code CopyOnWriteArrayList} per batchId
 * inside a {@code ConcurrentHashMap}, so concurrent writes during parallel processing
 * are safe.</p>
 */
@Slf4j
@Service
public class BatchSyncEventPublisher {

    /** Default SSE timeout: 10 minutes — sufficient for large batch operations. */
    private static final long SSE_TIMEOUT_MS = 10 * 60 * 1000L;

    private final Map<UUID, List<SseEmitter>> emitters = new ConcurrentHashMap<>();

    /**
     * Registers a new SSE connection for the given batch.
     * Called by the SSE endpoint when a client connects.
     */
    public SseEmitter subscribe(UUID batchId) {
        SseEmitter emitter = new SseEmitter(SSE_TIMEOUT_MS);
        emitters.computeIfAbsent(batchId, k -> new CopyOnWriteArrayList<>()).add(emitter);

        emitter.onCompletion(() -> removeEmitter(batchId, emitter));
        emitter.onTimeout(() -> {
            log.debug("SSE emitter timed out for batchId: {}", batchId);
            removeEmitter(batchId, emitter);
        });
        emitter.onError(e -> {
            log.debug("SSE emitter error for batchId: {}: {}", batchId, e.getMessage());
            removeEmitter(batchId, emitter);
        });

        log.info("New SSE subscriber for batchId: {} (total subscribers: {})",
                batchId, emitters.getOrDefault(batchId, List.of()).size());
        return emitter;
    }

    /**
     * Pushes a {@link FileSyncStatus} update to all clients subscribed to the given batch.
     * If a file has reached a terminal state and the batch is done, all emitters are completed.
     *
     * @param batchId the batch being tracked
     * @param status  the updated file status to push
     */
    public void emit(UUID batchId, FileSyncStatus status) {
        List<SseEmitter> batchEmitters = emitters.getOrDefault(batchId, List.of());
        if (batchEmitters.isEmpty()) return;

        SseEmitter.SseEventBuilder event = SseEmitter.event()
                .name("file-update")
                .data(status);

        batchEmitters.forEach(emitter -> {
            try {
                emitter.send(event);
            } catch (IOException e) {
                log.debug("Failed to send SSE event to subscriber for batchId: {}", batchId);
                removeEmitter(batchId, emitter);
            }
        });
    }

    /**
     * Sends a terminal event and completes all emitters for a batch.
     * Must be called by the batch orchestrator once all files reach a terminal state.
     */
    public void completeBatch(UUID batchId) {
        List<SseEmitter> batchEmitters = emitters.remove(batchId);
        if (batchEmitters == null) return;

        SseEmitter.SseEventBuilder doneEvent = SseEmitter.event().name("batch-complete").data("done");
        batchEmitters.forEach(emitter -> {
            try {
                emitter.send(doneEvent);
            } catch (IOException ignored) {
                // emitter may already be dead
            } finally {
                emitter.complete();
            }
        });
        log.info("Completed all SSE emitters for batchId: {}", batchId);
    }

    private void removeEmitter(UUID batchId, SseEmitter emitter) {
        List<SseEmitter> list = emitters.get(batchId);
        if (list != null) list.remove(emitter);
    }
}
