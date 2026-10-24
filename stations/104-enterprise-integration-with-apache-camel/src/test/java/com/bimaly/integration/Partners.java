package com.bimaly.integration;

import org.testcontainers.containers.GenericContainer;
import org.testcontainers.images.builder.Transferable;
import org.testcontainers.rabbitmq.RabbitMQContainer;

import java.io.IOException;
import java.nio.charset.StandardCharsets;

/**
 * A real RabbitMQ 4.1 and a real SFTP server (the bank's), started once for all tests. The bank's user has three
 * folders: upload (the app in ApiTest polls it), restart and old (the restart tests use them, so they never meet).
 */
final class Partners {

    static final RabbitMQContainer RABBIT = new RabbitMQContainer("rabbitmq:4.1-management-alpine");
    static final GenericContainer<?> SFTP = new GenericContainer<>("atmoz/sftp:alpine")
            .withCommand("koshbank:demo-only:1001::upload,restart,old").withExposedPorts(22);

    static {
        RABBIT.start();
        SFTP.start();
    }

    private Partners() {
    }

    static String sftp(String folder, int pollMillis) {
        return "sftp://koshbank@" + SFTP.getHost() + ":" + SFTP.getMappedPort(22) + "/" + folder
                + "?password=RAW(demo-only)&strictHostKeyChecking=no&delay=" + pollMillis;
    }

    /** As banks do it: write NAME.part, then rename, so the poller never sees half a file. */
    static void upload(String folder, String name, byte[] content) throws IOException, InterruptedException {
        String path = "/home/koshbank/" + folder + "/" + name;
        SFTP.copyFileToContainer(Transferable.of(content), path + ".part");
        var mv = SFTP.execInContainer("mv", path + ".part", path);
        if (mv.getExitCode() != 0) {
            throw new IllegalStateException(mv.getStderr());
        }
    }

    static void upload(String folder, String name, String content) throws IOException, InterruptedException {
        upload(folder, name, content.getBytes(StandardCharsets.UTF_8));
    }
}
