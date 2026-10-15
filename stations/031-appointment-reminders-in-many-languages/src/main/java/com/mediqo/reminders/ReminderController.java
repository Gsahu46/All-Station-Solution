package com.mediqo.reminders;

import jakarta.validation.constraints.Pattern;
import org.springframework.context.MessageSource;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.format.DateTimeFormatter;
import java.time.format.FormatStyle;
import java.util.List;
import java.util.Locale;

@RestController
class ReminderController {

    /** Languages with a complete message bundle. Anything else falls back to English. */
    static final List<Locale> SUPPORTED = List.of(Locale.ENGLISH, Locale.forLanguageTag("hi"));

    record Reminder(long appointmentId, String language, String requestedLanguage, String text) {
    }

    private final Appointments appointments;
    private final MessageSource messages;

    ReminderController(Appointments appointments, MessageSource messages) {
        this.appointments = appointments;
        this.messages = messages;
    }

    /**
     * The language, in order: ?lang, then the Accept-Language header, then the patient's preference. If none of them
     * is a language we have, English. The sentence is one template per language, so word order is the translator's.
     */
    @GetMapping("/appointments/{id}/reminder")
    Reminder reminder(@PathVariable long id,
                      @RequestParam(required = false) @Pattern(regexp = "[A-Za-z]{2,3}(-[A-Za-z]{2})?", message = "must be a language tag like hi or hi-IN") String lang,
                      @RequestHeader(value = "Accept-Language", required = false) String acceptLanguage) {
        Appointments.Appointment a = appointments.find(id).orElseThrow(() -> {
            ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, "No appointment " + id + ".");
            p.setTitle("Appointment not found");
            return new ErrorResponseException(HttpStatus.NOT_FOUND, p, null);
        });
        String requested = lang != null ? lang : acceptLanguage != null ? acceptLanguage : a.preferredLanguage();
        Locale locale = choose(requested);
        Locale formatting = Locale.of(locale.getLanguage(), "IN");   // month names in the language, India's conventions
        String text = messages.getMessage("reminder.text", new Object[]{
                a.patient(),
                a.doctor(),
                a.at().toLocalDate().format(DateTimeFormatter.ofLocalizedDate(FormatStyle.LONG).withLocale(formatting)),
                a.at().toLocalTime().format(DateTimeFormatter.ofPattern("HH:mm")),
                IndianRupees.format(a.amountPaise())}, locale);
        return new Reminder(id, locale.getLanguage(), requested, text);
    }

    /** Accept-Language-style matching ("hi-IN,hi;q=0.9,en;q=0.8"): the best supported language, else English. */
    static Locale choose(String requested) {
        try {
            Locale match = Locale.lookup(Locale.LanguageRange.parse(requested), SUPPORTED);
            return match != null ? match : Locale.ENGLISH;
        } catch (IllegalArgumentException malformedHeader) {
            return Locale.ENGLISH;
        }
    }
}
