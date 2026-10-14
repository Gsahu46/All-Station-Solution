package com.tijori.statementimport;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
class StatementController {

    /**
     * Reads a statement CSV and reports every line it could not read, with its line number. Nothing is stored:
     * the app shows the result and the customer fixes the listed lines.
     */
    // shortcut: the whole body is read into memory before the line limit applies; cap upload size at the proxy, or stream lines, for big files
    @PostMapping(path = "/statements/parse", consumes = "text/csv")
    StatementParser.Result parse(@RequestBody String csv) {
        try {
            return StatementParser.parse(csv);
        } catch (StatementParser.FileProblem e) {
            ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.UNPROCESSABLE_CONTENT, e.getMessage());
            p.setTitle("Statement file cannot be read");
            throw new ErrorResponseException(HttpStatus.UNPROCESSABLE_CONTENT, p, e);
        }
    }
}
