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

    /** Share with a user or a whole team, as viewer or editor, with a notice in the same transaction. */
    @Transactional
    void share(String user, String docId, String subject, String relation) {
        String access = permissions.access(user, docId).orElseThrow(Documents::notFound);
        // Anyone who can open a document may pass it on to a colleague, as with a link.
        String[] s = subject.split(":", 2);
        boolean known = s[0].equals("user") ? users.userExists(s[1])
                : jdbc.sql("SELECT EXISTS (SELECT 1 FROM relation_tuples WHERE object_type = 'team' AND object_id = ?)").param(s[1]).query(Boolean.class).single();
        if (!known) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "No such user or team");
        }
        // A team share is written as one row per member, so checks need no walk through teams.
        List<String> people = s[0].equals("user") ? List.of(s[1])
                : jdbc.sql("SELECT subject_id FROM relation_tuples WHERE object_type = 'team' AND object_id = ? AND relation = 'member' AND subject_type = 'user'")
                        .param(s[1]).query(String.class).list();
        for (String person : people) {
            jdbc.sql("""
                            INSERT INTO relation_tuples (object_type, object_id, relation, subject_type, subject_id, subject_relation)
                            VALUES ('doc', ?, ?, 'user', ?, '') ON CONFLICT DO NOTHING""")
                    .params(docId, relation, person).update();
        }
        jdbc.sql("INSERT INTO share_notices (doc_id, shared_to, relation, shared_by) VALUES (?, ?, ?, ?)").params(docId, subject, relation, user).update();
    }

    static ResponseStatusException notFound() {
        return new ResponseStatusException(HttpStatus.NOT_FOUND, "No such document");
    }
}
