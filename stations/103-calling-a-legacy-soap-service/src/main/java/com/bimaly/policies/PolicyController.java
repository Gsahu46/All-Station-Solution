package com.bimaly.policies;

import com.bimaly.policies.insurer.IssuePolicyRequest;
import com.bimaly.policies.insurer.IssuePolicyResponse;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Past;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import javax.xml.datatype.DatatypeFactory;
import java.net.URI;
import java.time.LocalDate;
import java.util.Locale;

@RestController
class PolicyController {

    record PolicyRequest(@NotBlank @Size(max = 100) String customerName, @NotNull @Past LocalDate dateOfBirth,
                         @NotBlank @Pattern(regexp = "[A-Za-z0-9]{3,10}") String productCode,
                         @Positive @Max(1_000_000_000_000L) long sumInsuredPaise) {
    }

    record Policy(String policyNumber, String productCode, long sumInsuredPaise, long premiumPaise) {
    }

    private static final Logger log = LoggerFactory.getLogger(PolicyController.class);
    private final InsurerClient insurer;

    PolicyController(InsurerClient insurer) {
        this.insurer = insurer;
    }

    /** Not retried on failure: the insurer's IssuePolicy is not idempotent, and a retry could issue two policies. */
    @PostMapping("/policies")
    ResponseEntity<Policy> issue(@Valid @RequestBody PolicyRequest body) {
        IssuePolicyRequest request = new IssuePolicyRequest();
        request.setCustomerName(body.customerName().strip());
        request.setDateOfBirth(DatatypeFactory.newDefaultInstance().newXMLGregorianCalendar(body.dateOfBirth().toString()));
        request.setProductCode(body.productCode().toUpperCase(Locale.ROOT));
        request.setSumInsuredPaise(body.sumInsuredPaise());
        IssuePolicyResponse issued = insurer.issue(request);
        return ResponseEntity.created(URI.create("/policies/" + issued.getPolicyNumber()))
                .body(new Policy(issued.getPolicyNumber(), request.getProductCode(), body.sumInsuredPaise(), issued.getPremiumPaise()));
    }

    /** The insurer said no. Its reason, if the fault was about our request; a gateway error if it was about itself. */
    @ExceptionHandler(InsurerClient.Refused.class)
    ResponseEntity<ProblemDetail> refused(InsurerClient.Refused e) {
        if (e.ourRequest) {
            ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.UNPROCESSABLE_CONTENT, "The insurer refused the policy: " + e.getMessage());
            problem.setProperty("insurerCode", e.code);
            return ResponseEntity.unprocessableContent().body(problem);
        }
        log.error("The insurer reported its own failure: {} {}", e.code, e.getMessage());
        return ResponseEntity.status(HttpStatus.BAD_GATEWAY)
                .body(ProblemDetail.forStatusAndDetail(HttpStatus.BAD_GATEWAY, "The insurer's system failed. Try again later."));
    }

    @ExceptionHandler(InsurerClient.Unreachable.class)
    ResponseEntity<ProblemDetail> unreachable(InsurerClient.Unreachable e) {
        log.error("No answer from the insurer: {}", e.getCause().getMessage());
        HttpStatus status = e.timedOut ? HttpStatus.GATEWAY_TIMEOUT : HttpStatus.BAD_GATEWAY;
        return ResponseEntity.status(status).body(ProblemDetail.forStatusAndDetail(status,
                e.timedOut ? "The insurer did not answer in time. The policy may or may not have been issued: check before trying again."
                        : "The insurer could not be reached. Try again later."));
    }
}
