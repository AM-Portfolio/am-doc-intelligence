package org.am.mypotrfolio.service.splitter;

import org.springframework.web.multipart.MultipartFile;

import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;

/**
 * Lightweight production-safe {@link MultipartFile} that wraps a byte array.
 *
 * <p>Used by {@link MultiSheetExcelSplitter} to materialise individual sheets
 * as independent file objects without depending on the test-only
 * {@code spring-test} jar ({@code MockMultipartFile}).</p>
 */
class InMemoryMultipartFile implements MultipartFile {

    private final String name;
    private final String originalFilename;
    private final String contentType;
    private final byte[] content;

    InMemoryMultipartFile(String name, String originalFilename, String contentType, byte[] content) {
        this.name = name;
        this.originalFilename = originalFilename;
        this.contentType = contentType;
        this.content = content != null ? content : new byte[0];
    }

    @Override public String getName() { return name; }
    @Override public String getOriginalFilename() { return originalFilename; }
    @Override public String getContentType() { return contentType; }
    @Override public boolean isEmpty() { return content.length == 0; }
    @Override public long getSize() { return content.length; }
    @Override public byte[] getBytes() { return content; }
    @Override public InputStream getInputStream() { return new ByteArrayInputStream(content); }

    @Override
    public void transferTo(File dest) throws IOException {
        try (var out = new java.io.FileOutputStream(dest)) {
            out.write(content);
        }
    }
}
