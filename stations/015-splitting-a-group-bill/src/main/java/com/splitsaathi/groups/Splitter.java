package com.splitsaathi.groups;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Splits an amount in whole paise so the parts always add up to the total: no paisa lost, none invented.
 * Division leaves a remainder; the remainder is handed out one paisa at a time, by a fixed rule, so the same
 * expense always splits the same way.
 */
final class Splitter {

    private Splitter() {
    }

    /** Rs 1,000 among 3: 33,333 paise each and 1 left over, which goes to the first person listed. */
    static Map<String, Long> equal(long totalPaise, List<String> people) {
        long each = totalPaise / people.size();
        long remainder = totalPaise % people.size();
        Map<String, Long> owed = new LinkedHashMap<>();
        for (int i = 0; i < people.size(); i++) {
            owed.put(people.get(i), each + (i < remainder ? 1 : 0));
        }
        return owed;
    }

    /**
     * Shares like 2:1:1. Each person first gets the whole paise of their exact share; the paise left over go one each
     * to the people whose exact share had the largest fraction cut off (ties: the order listed). This is the
     * "largest remainder" method.
     */
    static Map<String, Long> shares(long totalPaise, Map<String, Integer> shares) {
        long sum = shares.values().stream().mapToLong(Integer::longValue).sum();
        Map<String, Long> owed = new LinkedHashMap<>();
        List<Map.Entry<String, Long>> cutOff = new ArrayList<>(); // person -> remainder of totalPaise * share / sum
        long given = 0;
        for (Map.Entry<String, Integer> s : shares.entrySet()) {
            long exact = totalPaise * s.getValue();
            owed.put(s.getKey(), exact / sum);
            cutOff.add(Map.entry(s.getKey(), exact % sum));
            given += exact / sum;
        }
        cutOff.sort(Map.Entry.<String, Long>comparingByValue(Comparator.reverseOrder())); // stable: ties keep listed order
        for (int i = 0; i < totalPaise - given; i++) {
            owed.merge(cutOff.get(i).getKey(), 1L, Long::sum);
        }
        return owed;
    }
}
