package com.tiffino.addresses;

import tools.jackson.databind.JsonNode;

import java.util.HashMap;
import java.util.Map;
import java.util.Set;

/**
 * JSON Merge Patch (RFC 7396) for an address: a field that is present replaces the old value, a field set to
 * null removes it, a field left out is unchanged. Applying the same patch twice gives the same address,
 * so this PATCH is idempotent. (A patch like {"addToTip": 10} would not be.)
 */
final class MergePatch {

    static final Set<String> FIELDS = Set.of("line1", "line2", "landmark", "city", "pincode");

    private MergePatch() {
    }

    /** Returns the patched address, or throws IllegalArgumentException naming an unknown field or a non-text value. */
    static Address apply(Address current, JsonNode patch) {
        if (!patch.isObject()) {
            throw new IllegalArgumentException("The patch must be a JSON object.");
        }
        Map<String, String> v = new HashMap<>();
        v.put("line1", current.line1());
        v.put("line2", current.line2());
        v.put("landmark", current.landmark());
        v.put("city", current.city());
        v.put("pincode", current.pincode());
        for (Map.Entry<String, JsonNode> field : patch.properties()) {
            String name = field.getKey();
            JsonNode value = field.getValue();
            if (!FIELDS.contains(name)) {
                // The message names the allowed fields, never the one that was sent (no echo of client input).
                throw new IllegalArgumentException("Only line1, line2, landmark, city and pincode can be patched.");
            }
            if (!value.isNull() && !value.isString()) {
                throw new IllegalArgumentException("Every patched field must be text or null.");
            }
            v.put(name, value.isNull() ? null : value.asString());
        }
        return new Address(v.get("line1"), v.get("line2"), v.get("landmark"), v.get("city"), v.get("pincode"));
    }
}
