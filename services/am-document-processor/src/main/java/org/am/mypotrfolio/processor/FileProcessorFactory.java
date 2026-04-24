package org.am.mypotrfolio.processor;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

@Slf4j
@Component
public class FileProcessorFactory {
    private final List<FileProcessor> fileProcessors;

    public FileProcessorFactory(List<FileProcessor> fileProcessors) {
        this.fileProcessors = fileProcessors;
        log.info("FileProcessorFactory initialized with {} processors", fileProcessors.size());
        fileProcessors.forEach(processor -> 
            log.debug("Registered processor: {}", processor.getClass().getSimpleName()));
    }

    public FileProcessor getProcessor(MultipartFile file) {
        String filename = file.getOriginalFilename();
        log.debug("Getting processor for file: {}", filename);
        
        if (filename == null || !filename.contains(".")) {
            log.error("Invalid file format. Filename: {}", filename);
            throw new IllegalArgumentException("Invalid file format");
        }

        String extension = filename.substring(filename.lastIndexOf(".") + 1);
        log.debug("File extension detected: {}", extension);
        
        return fileProcessors.stream()
                .filter(processor -> {
                    boolean canProcess = processor.canProcess(extension);
                    if (canProcess) {
                        log.info("Found processor {} for file type: {}", 
                               processor.getClass().getSimpleName(), extension);
                    }
                    return canProcess;
                })
                .findFirst()
                .orElseThrow(() -> {
                    log.error("No processor found for file type: {}", extension);
                    return new IllegalArgumentException("Unsupported file type: " + extension);
                });
    }
}
