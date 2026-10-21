package com.taskloom.sharing;

import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.security.provisioning.UserDetailsManager;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;

@Service
class Documents {

    record Doc(String id, String title, String body, String yourAccess) {
    }

    private final JdbcClient jdbc;
    private final Permissions permissions;
    private final UserDetailsManager users;

    Documents(JdbcClient jdbc, Permissions permissions, UserDetailsManager users) {
        this.jdbc = jdbc;
        this.permissions = permissions;
        this.users = users;
    }

    /** No access at all is 404: a document's existence is as private as its text. */
    Doc open(String user, String docId) {
        String access = permissions.access(user, docId).orElseThrow(Documents::notFound);
        return jdbc.sql("SELECT id, title, body FROM documents WHERE id = ?").param(docId)
                .query((rs, n) -> new Doc(rs.getString(1), rs.getString(2), rs.getString(3), access)).single();
    }

    /**
     * Editors and owners may share as viewer or editor, with a user or a whole team. One tuple, and a notice in the
     * same transaction. The team's members are never copied: whoever is in the team at the time of each request has access.
     */
    @Transactional
    void share(String user, String docId, String subject, String relation) {
        String access = permissions.access(user, docId).orElseThrow(Documents::notFound);
        if (access.equals("viewer")) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Viewers cannot share");
        }
        String[] s = subject.split(":", 2);
        boolean known = s[0].equals("user") ? users.userExists(s[1])
                : jdbc.sql("SELECT EXISTS (SELECT 1 FROM relation_tuples WHERE object_type = 'team' AND object_id = ?)").param(s[1]).query(Boolean.class).single();
        if (!known) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "No such user or team");
        }
        jdbc.sql("""
                        INSERT INTO relation_tuples (object_type, object_id, relation, subject_type, subject_id, subject_relation)
                        VALUES ('doc', ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING""")
                .params(docId, relation, s[0], s[1], s[0].equals("team") ? "member" : "").update();
        jdbc.sql("INSERT INTO share_notices (doc_id, shared_to, relation, shared_by) VALUES (?, ?, ?, ?)").params(docId, subject, relation, user).update();
    }

    /** Editors and owners only: who else can read a document is itself something to protect. */
    List<Permissions.Holder> holders(String user, String docId) {
        editorOrOwner(user, docId);
        return permissions.holders(docId);
    }

    @Transactional
    void unshare(String user, String docId, String subject) {
        editorOrOwner(user, docId);
        String[] s = subject.split(":", 2);
        if (s.length != 2) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Subject is user:name or team:name");
        }
        jdbc.sql("DELETE FROM relation_tuples WHERE object_type = 'doc' AND object_id = ? AND relation IN ('viewer', 'editor') AND subject_type = ? AND subject_id = ?")
                .params(docId, s[0], s[1]).update();
    }

    private void editorOrOwner(String user, String docId) {
        if (permissions.access(user, docId).orElseThrow(Documents::notFound).equals("viewer")) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Viewers cannot do this");
        }
    }

    static ResponseStatusException notFound() {
        return new ResponseStatusException(HttpStatus.NOT_FOUND, "No such document");
    }
}
