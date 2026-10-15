package com.tiffino.reports;

import org.springframework.stereotype.Component;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Tiffino's 40 outlets (demo): ids TF-01 to TF-40. */
@Component
class Outlets {

    static final List<String> AREAS = List.of(
            "Koramangala", "Indiranagar", "HSR Layout", "Whitefield", "Jayanagar", "Malleshwaram", "BTM Layout", "Marathahalli",
            "Electronic City", "Hebbal", "Yelahanka", "Banashankari", "JP Nagar", "Rajajinagar", "Bellandur", "Sarjapur Road",
            "Kalyan Nagar", "Basavanagudi", "Frazer Town", "Ulsoor", "Koregaon Park", "Viman Nagar", "Kothrud", "Baner",
            "Aundh", "Hinjewadi", "Wakad", "Hadapsar", "Kharadi", "Shivajinagar", "Camp", "Deccan",
            "Magarpatta", "Pimple Saudagar", "Kalyani Nagar", "Sinhagad Road", "Bavdhan", "Wagholi", "Undri", "Erandwane");

    private final Map<String, String> names = new LinkedHashMap<>();

    Outlets() {
        for (int i = 0; i < AREAS.size(); i++) {
            names.put("TF-%02d".formatted(i + 1), "Tiffino " + AREAS.get(i));
        }
    }

    String name(String outletId) {
        return names.getOrDefault(outletId, outletId);
    }

    /** The first 20 outlets are in Bengaluru, the rest in Pune (demo). */
    String city(String outletId) {
        return Integer.parseInt(outletId.substring(3)) <= 20 ? "Bengaluru" : "Pune";
    }

    List<String> ids() {
        return List.copyOf(names.keySet());
    }
}
