// package org.am.mypotrfolio.service;

// import lombok.RequiredArgsConstructor;
// import lombok.SneakyThrows;
// import org.am.mypotrfolio.utils.NseFileBuilder;
// import org.springframework.stereotype.Service;

// import java.io.File;
// import java.io.IOException;
// import java.nio.file.Files;
// import java.nio.file.Path;
// import java.nio.file.Paths;
// import java.util.LinkedList;
// import java.util.List;

// @Service
// @RequiredArgsConstructor
// public class MutualFundService {

//     private final NseFileBuilder nseFileBuilder;


//     @SneakyThrows
//     public void uploadMutualFundFiles(String folderName){

//         String filePath = "C:\\Users\\MKU257\\Downloads\\PortfolioMasterData\\"+folderName;
//         Path testFolderPath = Paths.get(filePath);
//         if (Files.exists(testFolderPath)) {
//             ExcelProcessor processor = new ExcelProcessor();

//             List<File> files = processor.getAllFiles();
//             System.out.println("Files: " + files);

//             List<String> fileNames = processor.getAllFileNames();
//             System.out.println("File Names: " + fileNames);

//             List<Path> filePaths = processor.getAllFilePaths();
//             System.out.println("File Paths: " + filePaths);

//             List<MutualFunds> list = new LinkedList<>();
//             files.forEach(file -> {
//                 try {
//                   var funds =   processor.processFiles(fileProcessorLambda -> fileProcessorLambda.processFile(file));
//                   list.addAll(funds);
//                 } catch (IOException e) {
//                     throw new RuntimeException(e);
//                 }
//             });

//             //nseFileBuilder.writeToMutualExcel(list);

//            // System.out.println("Processed Data: " + processedData);
//         }
//     }
// }
