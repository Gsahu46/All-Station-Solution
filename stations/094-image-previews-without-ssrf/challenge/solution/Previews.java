package com.chaupal.previews;

import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

import java.net.URI;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** A preview of a link for a member's draft post: the page's title, description and image link. */
@Service
class Previews {

    record Preview(String id, String url, String title, String description, String imageUrl) {
    }

    private record Owned(String owner, Preview preview) {
    }

    private static final Pattern TITLE = Pattern.compile("<title[^>]*>(.*?)</title>", Pattern.CASE_INSENSITIVE | Pattern.DOTALL);

    private final SafeFetcher fetcher;
    // shortcut: previews are kept in memory and lost on restart; a real service would cache them in a store with an expiry.
    private final Map<String, Owned> byId = new ConcurrentHashMap<>();

    Previews(SafeFetcher fetcher) {
        this.fetcher = fetcher;
    }

    Preview create(String owner, URI url) {
        SafeFetcher.Page page = fetcher.fetch(url);
        String title = meta(page.html(), "og:title");
        if (title == null) {
            Matcher m = TITLE.matcher(page.html());
            title = m.find() ? unescape(m.group(1).strip()) : null;
        }
        Preview p = new Preview(UUID.randomUUID().toString(), url.toString(), title, meta(page.html(), "og:description"), image(page));
        byId.put(p.id(), new Owned(owner, p));
        return p;
    }

    /** A draft's preview is its owner's: anyone else gets "not found", which says nothing about whether it exists. */
    Preview get(String owner, String id) {
        Owned o = byId.get(id);
        if (o == null || !o.owner().equals(owner)) {
            throw SafeFetcher.problem(HttpStatus.NOT_FOUND, "No such preview");
        }
        return o.preview();
    }

    /** Fetches the preview's image with the same checks as the page: only images, at most 1 MB. */
    SafeFetcher.Fetched image(String owner, String id) {
        Preview p = get(owner, id);
        if (p.imageUrl() == null) {
            throw SafeFetcher.problem(HttpStatus.NOT_FOUND, "This preview has no image");
        }
        return fetcher.fetch(URI.create(p.imageUrl()), "image/", 1024 * 1024, "The image link is not an image");
    }

    /** The image is only linked, never fetched by the server: fetching it would need the same checks as the page. */
    private static String image(SafeFetcher.Page page) {
        String src = meta(page.html(), "og:image");
        if (src == null) {
            return null;
        }
        try {
            URI resolved = page.finalUri().resolve(src.strip());
            return resolved.getScheme() != null && resolved.getScheme().matches("(?i)https?") ? resolved.toString() : null;
        } catch (IllegalArgumentException e) {
            return null;
        }
    }

    private static String meta(String html, String property) {
        Matcher m = Pattern.compile("<meta[^>]+property=[\"']" + Pattern.quote(property) + "[\"'][^>]*content=[\"']([^\"']*)[\"']", Pattern.CASE_INSENSITIVE).matcher(html);
        return m.find() ? unescape(m.group(1).strip()) : null;
    }

    private static String unescape(String s) {
        return s.replace("&quot;", "\"").replace("&#39;", "'").replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&");
    }
}
