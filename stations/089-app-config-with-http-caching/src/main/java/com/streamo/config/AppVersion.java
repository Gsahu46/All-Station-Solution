package com.streamo.config;

/** An app version like 5.10.2, compared number by number: as text, "5.10.0" would sort before "5.9.0". */
record AppVersion(int major, int minor, int patch) implements Comparable<AppVersion> {

    static AppVersion parse(String text) {
        String[] p = text.split("\\.");
        return new AppVersion(Integer.parseInt(p[0]), Integer.parseInt(p[1]), Integer.parseInt(p[2]));
    }

    @Override
    public int compareTo(AppVersion o) {
        return major != o.major ? Integer.compare(major, o.major) : minor != o.minor ? Integer.compare(minor, o.minor) : Integer.compare(patch, o.patch);
    }

    @Override
    public String toString() {
        return major + "." + minor + "." + patch;
    }
}
