package com.tiffino.ordering;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import javax.tools.Diagnostic;
import javax.tools.DiagnosticCollector;
import javax.tools.JavaCompiler;
import javax.tools.JavaFileObject;
import javax.tools.StandardJavaFileManager;
import javax.tools.ToolProvider;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.stream.Collectors;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The first test written for this station: the old mapper drops the field nobody remembered, MapStruct keeps it, and
 * the compiler itself refuses a mapper that forgets one. The last two tests run javac with the MapStruct processor.
 */
class HandWrittenMappingTrapTest extends ApiTest {

    @Test
    void theHandWrittenMapperDropsDeliveryInstructions() {
        Order entity = OldOrderMapper.toEntity(request(ORDER));
        assertThat(entity.getDeliveryInstructions()).isNull();                        // lost on the way in
        entity.setDeliveryInstructions("Ring twice, baby sleeping");
        assertThat(OldOrderMapper.toResponse(entity).deliveryInstructions()).isNull();   // and on the way out
    }

    @Test
    void mapStructCarriesItBothWays() {
        Order entity = mapper.toEntity(request(ORDER));
        assertThat(entity.getDeliveryInstructions()).isEqualTo("Ring twice, baby sleeping");
        assertThat(entity.getLines()).allSatisfy(line -> assertThat(line.getOrder()).isSameAs(entity));
        entity.setStatus("PLACED");
        assertThat(mapper.toResponse(entity).deliveryInstructions()).isEqualTo("Ring twice, baby sleeping");
    }

    /** Compiles one mapper source with the MapStruct processor; returns the error messages. */
    static List<String> compile(Path dir, String source) throws IOException {
        Path src = dir.resolve("src/demo/M.java");
        Files.createDirectories(src.getParent());
        Files.writeString(src, source);
        Files.createDirectories(dir.resolve("out"));
        JavaCompiler javac = ToolProvider.getSystemJavaCompiler();
        DiagnosticCollector<JavaFileObject> diagnostics = new DiagnosticCollector<>();
        try (StandardJavaFileManager files = javac.getStandardFileManager(diagnostics, null, null)) {
            javac.getTask(null, files, diagnostics,
                    List.of("-proc:full", "-classpath", System.getProperty("java.class.path"), "-d", dir.resolve("out").toString(), "-s", dir.resolve("out").toString()),
                    null, files.getJavaFileObjects(src)).call();
        }
        return diagnostics.getDiagnostics().stream().filter(d -> d.getKind() == Diagnostic.Kind.ERROR)
                .map(d -> d.getMessage(null)).collect(Collectors.toList());
    }

    @Test
    void theBuildFailsWhenAMapperMissesAField(@TempDir Path dir) throws IOException {
        List<String> errors = compile(dir, """
                package demo;
                import org.mapstruct.*;
                @Mapper(unmappedTargetPolicy = ReportingPolicy.ERROR)
                interface M {
                    record Source(String customerName) {}
                    record Target(String customerName, String deliveryInstructions) {}
                    Target map(Source source);
                }""");
        assertThat(errors).anySatisfy(e -> assertThat(e).contains("Unmapped target property: \"deliveryInstructions\""));
    }

    @Test
    void butAPackagePrivateSetterIsInvisibleAndSilentlySkipped(@TempDir Path dir) throws IOException {
        // Found while building this station: with package-private setters, MapStruct mapped only the list and said nothing.
        List<String> errors = compile(dir, """
                package demo;
                import org.mapstruct.*;
                @Mapper(unmappedTargetPolicy = ReportingPolicy.ERROR)
                interface M {
                    record Source(String customerName) {}
                    class Target {
                        private String customerName;
                        public String getCustomerName() { return customerName; }
                        void setCustomerName(String customerName) { this.customerName = customerName; }
                    }
                    Target map(Source source);
                }""");
        assertThat(errors).isEmpty();
        assertThat(Files.readString(dir.resolve("out/demo/MImpl.java"))).doesNotContain("setCustomerName");
    }
}
