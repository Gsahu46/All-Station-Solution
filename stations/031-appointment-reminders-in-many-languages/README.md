# Station 031 · Appointment reminders in many languages

Foundations · 0–1 years · Core · Healthcare · Types: none

Spring Boot 4.1.1 · Java 25 · MessageSource · message bundles · Accept-Language · Locale.lookup · Indian number formatting · MockMvc. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Appointments, patients and amounts are demo data, not Mediqo's. The endpoint builds the reminder text only; no SMS or message is sent. The Hindi text was written for this demo and should be reviewed by a native speaker before real use.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 12 tests.

# 1 · Understand

## The problem in real life

1.  **A reminder goes out**

    Asha prefers Hindi. The app sends her: "नमस्ते Asha, आपका अपॉइंटमेंट डॉ. Mehta के साथ 20 October 2026। कृपया भुगतान करें 123456.5".

2.  **Three things are wrong**

    The sentence was glued from Hindi pieces in English word order, the month is in English, and 123456.5 has no rupee sign, no grouping and one decimal. Asha calls the clinic to ask what she owes.

3.  **The fix**

    One whole sentence per language with numbered blanks, the date formatted in the patient's language, and the amount written the Indian way: ₹1,23,456.50.

Translate whole sentences, and format numbers and dates for the reader, not for the server.

## What are we building?

`GET /appointments/{id}/reminder` returns the reminder text for an appointment in the right language: the one asked for with `?lang`, else the phone's language, else the patient's own preference. If we do not have that language, English.

## An everyday analogy

A wedding card printed in two languages. The Hindi side is not the English side with words swapped one by one; someone wrote the whole Hindi text, and only the names and the date are filled in.

## How it works in 4 steps

1.  **Pick the language**: `?lang`, then the `Accept-Language` header, then the patient's preference.
2.  **Match it** to the languages we have (English, Hindi); anything else becomes English.
3.  **Format the pieces**: the date in that language, the amount as Indian rupees.
4.  **Fill the sentence** for that language, where the translator decided the word order.

Check yourself: why not translate "Hello", "your appointment with" and "is on" separately and join them?

Languages order words differently. Hindi puts the verb at the end and uses endings like "के साथ" after the name. Joined fragments follow English order, so the sentence is wrong in every language but English.

## What this station is not

- **No sending.** The text is built; no SMS or WhatsApp message is sent.
- **No translation service.** The texts are written by people and kept in files.
- **Two languages.** English and Hindi; challenge 1 adds Marathi.

## Key terms

| Term                  | Simple meaning                                                             | Everyday example                                              | In this project                |
|-----------------------|----------------------------------------------------------------------------|---------------------------------------------------------------|--------------------------------|
| **Message bundle**    | A file of texts for one language, each under a key.                        | The same notice printed in two languages on a hospital wall.  | `messages_hi.properties`       |
| **Placeholder**       | A numbered gap in a message that the app fills: `{0}`, `{1}`.              | Blanks in a form letter.                                      | `{0}` is the patient's name    |
| **Locale**            | A language plus regional conventions: month names, digits, separators.     | Writing a date the way people in that place read it.          | `hi-IN`                        |
| **Accept-Language**   | A header the phone or browser sends to say which languages the user reads. | Telling the receptionist "Hindi please, English is fine too". | `hi-IN,hi;q=0.9,en;q=0.8`      |
| **Fallback language** | The language used when we have no text in the one asked for.               | Using the English leaflet when the Tamil one has run out.     | English, `messages.properties` |
| **Lakh grouping**     | Indian digit grouping: the last three digits, then pairs.                  | ₹1,23,456 is one lakh twenty-three thousand.                  | `IndianRupees`                 |

# 2 · Build: Spec

## Business problem

**Mediqo** (a fictional clinic chain) sends appointment reminders. Hindi-speaking patients get sentences glued from fragments, with English month names, and amounts like 123456.5 instead of ₹1,23,456.50.

## Acceptance criteria

1.  **Given** `?lang=en` and a Hindi `Accept-Language`, **then** the reminder is in English: `lang` wins.
2.  **Given** no `lang` and `Accept-Language: hi-IN,hi;q=0.9,en;q=0.8`, **then** Hindi.
3.  **Given** neither, **then** the patient's preferred language: Hindi for Asha, English for Ravi.
4.  **Given** Tamil, which we do not have, **then** English, and the response still says Tamil was requested.
5.  **Given** Asha's ₹1,23,456.50 appointment on 20 October 2026 at 10:30, in Hindi, **then** exactly: नमस्ते Asha, डॉ. Mehta के साथ आपका अपॉइंटमेंट 20 अक्टूबर 2026 को 10:30 बजे है। कृपया क्लिनिक में ₹1,23,456.50 का भुगतान करें।
6.  **Given** an unknown appointment, **then** `404`; a `lang` that is not a language tag, `400`.

## Requirements

- One complete sentence per language, with numbered placeholders; every key in every bundle, with the same placeholders.
- English is the only fallback, whatever language the server itself runs in.
- Money stays in integer paise until it is formatted: ₹, lakh and crore grouping, two decimals.
- Times are 24-hour (`10:30`, `15:00`), so no translated AM/PM is needed.

## Learning objectives

- Use Spring's `MessageSource` with message bundles and placeholders.
- Choose a language from `Accept-Language` with `Locale.lookup`.
- Format dates with a `Locale`, and know where Java's number formatting stops (lakh grouping).
- Control the fallback language.

# 2 · Build: API contract

## Endpoints

| Method | Path                                  | Purpose                                                                    |
|--------|---------------------------------------|----------------------------------------------------------------------------|
| `GET`  | `/appointments/{id}/reminder?lang=hi` | The reminder text. `lang` is optional; so is the `Accept-Language` header. |

## Response fields

| Field               | Meaning                                                                                                                                    |
|---------------------|--------------------------------------------------------------------------------------------------------------------------------------------|
| `language`          | The language the text is in: `en` or `hi`.                                                                                                 |
| `requestedLanguage` | What was asked for (or the patient's preference). Differs from `language` after a fallback, so a dashboard can count missing translations. |
| `text`              | The reminder.                                                                                                                              |

## Status codes

| Status | When                                                              |
|--------|-------------------------------------------------------------------|
| 200    | A reminder, in the chosen language or in English after a fallback |
| 400    | `lang` is not a language tag such as `hi` or `hi-IN`              |
| 404    | No such appointment                                               |

## Captured examples

Captured with curl from the running app on 15 Oct 2026. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: Asha, nothing asked for

**Why:** no `lang`, no header: her preference, Hindi. Month in Hindi, amount in lakhs.

Request

``` code
GET /appointments/501/reminder HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 339

{
  "appointmentId": 501,
  "language": "hi",
  "requestedLanguage": "hi",
  "text": "नमस्ते Asha, डॉ. Mehta के साथ आपका अपॉइंटमेंट 20 अक्टूबर 2026 को 10:30 बजे है। कृपया क्लिनिक में ₹1,23,456.50 का भुगतान करें।"
}
```

### Case 2: Asha, `?lang=en`

**Why:** `lang` wins over her preference. The amount is still grouped the Indian way.

Request

``` code
GET /appointments/501/reminder?lang=en HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 187

{
  "appointmentId": 501,
  "language": "en",
  "requestedLanguage": "en",
  "text": "Hello Asha, your appointment with Dr Mehta is on 20 October 2026 at 10:30. Please pay ₹1,23,456.50 at the clinic."
}
```

### Case 3: Ravi's phone is set to Hindi

**Why:** the header beats his saved preference (English).

Request

``` code
GET /appointments/502/reminder HTTP/1.1
Accept-Language: hi-IN,hi;q=0.9,en;q=0.8
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 354

{
  "appointmentId": 502,
  "language": "hi",
  "requestedLanguage": "hi-IN,hi;q=0.9,en;q=0.8",
  "text": "नमस्ते Ravi, डॉ. Iyer के साथ आपका अपॉइंटमेंट 21 अक्टूबर 2026 को 15:00 बजे है। कृपया क्लिनिक में ₹500.00 का भुगतान करें।"
}
```

### Case 4: `?lang=ta`

**Why:** no Tamil bundle yet: English, and `requestedLanguage` says Tamil was asked for.

Request

``` code
GET /appointments/501/reminder?lang=ta HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 187

{
  "appointmentId": 501,
  "language": "en",
  "requestedLanguage": "ta",
  "text": "Hello Asha, your appointment with Dr Mehta is on 20 October 2026 at 10:30. Please pay ₹1,23,456.50 at the clinic."
}
```

### Case 5: appointment 999

**Why:** `404`.

Request

``` code
GET /appointments/999/reminder HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No appointment 999.",
  "instance": "/appointments/999/reminder",
  "status": 404,
  "title": "Appointment not found"
}
```

### Case 6: `?lang=hindi-language`

**Why:** not a language tag: `400`.

Request

``` code
GET /appointments/501/reminder?lang=hindi-language HTTP/1.1
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Validation failure",
  "instance": "/appointments/501/reminder",
  "status": 400,
  "title": "Bad Request"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                              | What happens                       | Proved by                                                |
|-------------------------------------------------------------------|------------------------------------|----------------------------------------------------------|
| `lang` and a header disagree                                      | `lang` wins                        | `theLangParameterWins`                                   |
| Only a header, with weights                                       | The best language we have          | `withoutLangTheAcceptLanguageHeaderDecides`              |
| Nothing asked                                                     | The patient's preference           | `withNeitherThePatientsPreferenceDecides`                |
| Tamil; a header of Tamil and Malayalam                            | English, with the request recorded | `aLanguageWeDoNotHaveFallsBackToEnglish`                 |
| A server whose own locale is Hindi                                | The fallback is still English      | `theServersOwnLocaleNeverDecidesTheFallback`             |
| A malformed `Accept-Language`                                     | English, not an error              | `languageMatchingFollowsAcceptLanguageRules`             |
| ₹0.05, ₹999.99, ₹1,000.00 up to ₹10,00,00,000.00                  | Indian grouping, two decimals      | `rupeesAreGroupedInLakhsAndCrores`                       |
| A message missing from the Hindi bundle, or a placeholder dropped | A test fails before release        | `everyEnglishMessageHasAHindiOneWithTheSamePlaceholders` |
| Appointment 999; `lang=<script>`                                  | `404`; `400`                       | `anUnknownAppointmentIs404AndAMalformedLangIs400`        |

## The trap

Plausible but wrong

Concatenating translated fragments, and formatting numbers without the locale.

The first test rebuilds the old reminder: the Hindi text ends in `123456.5`, contains "October", and has lost the verb ending. The second shows the obvious fix is not enough: Java's own `en-IN` currency format gives `₹123,456.50`, grouped in threes, because `DecimalFormat` has a single grouping size. The third checks the real Hindi sentence word for word. While building, each fix was undone once: Java's formatter instead of `IndianRupees` turned 4 tests red, English dates everywhere 5, ignoring the header 2, and falling back to the server's locale 1.

``` code
package com.mediqo.reminders;

import org.junit.jupiter.api.Test;

import java.text.NumberFormat;
import java.util.Locale;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/** The first test written for this station: it reproduces the bugs before the fix. */
class ConcatenatedReminderTrapTest extends ApiTest {

    /** The "before" bundles: translated fragments, glued together in English word order. Kept only in tests. */
    static final Map<String, Map<String, String>> FRAGMENTS = Map.of(
            "en", Map.of("hello", "Hello ", "with", ", your appointment with Dr ", "on", " is on ", "pay", ". Please pay "),
            "hi", Map.of("hello", "नमस्ते ", "with", ", आपका अपॉइंटमेंट डॉ. ", "on", " के साथ ", "pay", "। कृपया भुगतान करें "));

    static String oldReminder(String lang, String patient, String doctor, String date, long amountPaise) {
        Map<String, String> f = FRAGMENTS.get(lang);
        return f.get("hello") + patient + f.get("with") + doctor + f.get("on") + date + f.get("pay") + (amountPaise / 100.0);
    }

    @Test
    void theOldAmountIsAPlainDoubleAndTheOldDateIsEnglishEverywhere() {
        String hi = oldReminder("hi", "Asha", "Mehta", "20 October 2026", 12_345_650);
        assertThat(hi).endsWith("123456.5");             // no rupee sign, no grouping, one decimal
        assertThat(hi).contains("October");               // the date was formatted once, in English
        assertThat(hi).doesNotContain("को");              // and the Hindi sentence is missing its verb ending: glued, not translated
    }

    @Test
    void javasOwnIndianFormatterGroupsInThrees() {
        // The obvious fix is not enough: DecimalFormat supports one grouping size, so lakhs are missed.
        assertThat(NumberFormat.getCurrencyInstance(Locale.forLanguageTag("en-IN")).format(123_456.50)).isEqualTo("₹123,456.50");
        assertThat(IndianRupees.format(12_345_650)).isEqualTo("₹1,23,456.50");
    }

    @Test
    void theRealReminderIsOneHindiSentenceWithIndianFormatting() throws Exception {
        reminder(501, "hi", null).andExpect(jsonPath("$.text").value(ASHA_HI));
    }
}
```

# 2 · Build: Set up & code

## Set up and run

| You need | Version                                         | Check with      |
|----------|-------------------------------------------------|-----------------|
| JDK      | 25 (recommended). JDK 21 also works, see below  | `java -version` |
| Maven    | Not needed: the project ships the Maven wrapper |                 |
| Docker   | Not needed for this station                     |                 |

**macOS / Linux**

``` code
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all 12 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Ask as a phone set to Hindi would, then as one set to Tamil:

``` code
curl http://localhost:8080/appointments/502/reminder -H "Accept-Language: hi-IN,hi;q=0.9,en;q=0.8"
curl http://localhost:8080/appointments/502/reminder -H "Accept-Language: ta-IN"
```

## Troubleshooting

| You see                                                               | Cause                                                            | Fix                                                                                                         |
|-----------------------------------------------------------------------|------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------|
| Hindi shows as `à¤¨à¤®...` or `?????`                                 | The bundle was read as ISO-8859-1, or the terminal is not UTF-8. | Keep `spring.messages.encoding: UTF-8` and save bundles as UTF-8. On Windows, run `chcp 65001` before curl. |
| The key itself (`reminder.text`) appears, or `NoSuchMessageException` | The key is missing from `messages.properties`.                   | Add it to the English file first: it is the fallback for every language.                                    |
| A message shows `{1}` unfilled, or an apostrophe disappears           | MessageFormat treats `'` as a quote character.                   | Write `''` for an apostrophe in a message that has placeholders.                                            |

## Project layout

``` tree
stations/031-appointment-reminders-in-many-languages/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/mediqo/reminders/
│   ├── ReminderController.java   ├── IndianRupees.java
│   ├── Appointments.java         └── RemindersApplication.java
├── src/main/resources/
│   ├── application.yaml   ├── messages.properties   └── messages_hi.properties
├── src/test/java/com/mediqo/reminders/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the texts behind it.

#### `src/main/java/com/mediqo/reminders/ReminderController.java`

Does  
Chooses the language, formats the date and amount, and fills the sentence.

Why  
`Locale.lookup` applies `Accept-Language` weights for us; anything unmatched or malformed is English.

Without it  
Joining fragments: the word order is then English in every language.

- The formatting locale is `<language>-IN`: Hindi month names with India's conventions.
- `@Pattern` on `lang` refuses anything that is not a language tag.

#### `src/main/java/com/mediqo/reminders/IndianRupees.java`

Does  
Paise to `₹1,23,456.50`.

Why  
Integer arithmetic only; the grouping is done by hand because Java's formatter cannot do it.

Without it  
`paise / 100.0` printed as a double, or `NumberFormat` for `en-IN`.

#### `src/main/resources/messages.properties`

English, the fallback: one sentence, five placeholders.

#### `src/main/resources/messages_hi.properties`

Hindi: the same placeholders in Hindi word order. Saved as UTF-8.

#### `src/main/resources/application.yaml`

The bundle name, UTF-8, and no fallback to the server's own locale.

#### `src/main/java/com/mediqo/reminders/Appointments.java`

Two demo appointments, each with the patient's preferred language.

#### `src/main/java/com/mediqo/reminders/RemindersApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                           | Test class                         | Result |
|---------------|-------------------------------------------------------|------------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found              | `ReminderContractTest` (6)         | pass   |
| Every station | Reproduce the failure before the fix                  | `ConcatenatedReminderTrapTest` (3) | pass   |
| This station  | Bundles complete, rupee formatting, language matching | `MessagesTest` (3)                 | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 6, Failures: 0, Errors: 0, Skipped: 0 -- in com.mediqo.reminders.ReminderContractTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.mediqo.reminders.MessagesTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.mediqo.reminders.ConcatenatedReminderTrapTest
[INFO] Tests run: 12, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/mediqo/reminders/ConcatenatedReminderTrapTest.java`

Written first: the old fragments, Java's own en-IN format, and the real Hindi sentence.

#### `src/test/java/com/mediqo/reminders/ReminderContractTest.java`

Which language wins, the fallback, the server's locale, and every refusal.

#### `src/test/java/com/mediqo/reminders/MessagesTest.java`

No Spring: every key in both bundles with the same placeholders, a table of amounts, and the matching rules.

#### `src/test/java/com/mediqo/reminders/ApiTest.java`

Shared setup and the two expected sentences for Asha.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/mediqo/reminders/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=MarathiChallengeTest`.
3.  Change the code until it passes, then run `./mvnw test` to check the other 12 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 16 tests pass (12 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## Add Marathi

Mediqo opens a clinic in Pune. Add Marathi (`mr`): a bundle with every key and the same placeholders, chosen by `?lang=mr` or a Marathi `Accept-Language`.

**Done when:** both tests in `MarathiChallengeTest` pass.

Hints

- A new file `messages_mr.properties` next to the others, saved as UTF-8.
- Spring finds the file on its own; the controller only needs to know Marathi is supported.

#### `challenge/MarathiChallengeTest.java`

``` code
package com.mediqo.reminders;

import org.junit.jupiter.api.Test;

import java.util.Properties;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * Challenge 1: Mediqo opens a clinic in Pune. Add Marathi ("mr"): a messages_mr.properties with every key, the same
 * placeholders, and Marathi chosen by ?lang or Accept-Language. Dates use Java's own Marathi month names.
 */
class MarathiChallengeTest extends ApiTest {

    @Test
    void marathiIsChosenByLangOrByTheHeader() throws Exception {
        reminder(501, "mr", null).andExpect(jsonPath("$.language").value("mr"))
                .andExpect(jsonPath("$.text", org.hamcrest.Matchers.allOf(
                        org.hamcrest.Matchers.startsWith("नमस्कार Asha"),
                        org.hamcrest.Matchers.containsString("20 ऑक्टोबर, 2026"),
                        org.hamcrest.Matchers.containsString("₹1,23,456.50"))));
        reminder(502, null, "mr-IN,hi;q=0.8").andExpect(jsonPath("$.language").value("mr"));
    }

    @Test
    void theMarathiBundleHasEveryKeyWithTheSamePlaceholders() throws Exception {
        Properties en = MessagesTest.bundle("messages.properties");
        Properties mr = MessagesTest.bundle("messages_mr.properties");
        assertThat(mr.stringPropertyNames()).containsExactlyInAnyOrderElementsOf(en.stringPropertyNames());
        for (String key : en.stringPropertyNames()) {
            assertThat(MessagesTest.placeholders(mr.getProperty(key))).as(key).isEqualTo(MessagesTest.placeholders(en.getProperty(key)));
        }
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 35 minutes

## Today, tomorrow, or in N days

Add a `when` field: "today", "tomorrow" or "in 5 days" (Hindi: आज, कल, 5 दिन में), from one message per language, not from `if`/`else` in Java. Count days in India's time zone from a `Clock` bean.

**Done when:** both tests in `WhenChallengeTest` pass, and the station's tests still pass.

Hints

- MessageFormat's choice format: `{0,choice,0#today|1#tomorrow|1<in {0} days}`.
- `LocalDate.now(clock.withZone(ZoneId.of("Asia/Kolkata")))`: at 20:00 UTC on the 19th it is already the 20th in India.

#### `challenge/WhenChallengeTest.java`

``` code
package com.mediqo.reminders;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZoneOffset;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * Challenge 2: add a "when" field to the reminder: "today", "tomorrow" or "in 5 days" (in Hindi: आज, कल, 5 दिन में),
 * from one message with a choice format, not from if/else in Java. Days are counted in India's time zone, from a
 * Clock bean, so a test can set "now".
 */
@Import(WhenChallengeTest.TestClock.class)
class WhenChallengeTest extends ApiTest {

    /** A clock the test moves by hand. Starts at the Unix epoch, in UTC like a typical server. */
    static class SettableClock extends Clock {
        volatile Instant now = Instant.EPOCH;

        @Override
        public ZoneId getZone() {
            return ZoneOffset.UTC;
        }

        @Override
        public Clock withZone(ZoneId zone) {
            return Clock.fixed(now, zone);
        }

        @Override
        public Instant instant() {
            return now;
        }
    }

    @TestConfiguration
    static class TestClock {
        @Bean
        @Primary
        SettableClock settableClock() {
            return new SettableClock();
        }
    }

    @Autowired
    SettableClock clock;

    @Test
    void daysUntilTheAppointmentInBothLanguages() throws Exception {
        clock.now = Instant.parse("2026-10-15T06:00:00Z");   // Asha's appointment is on 20 October
        reminder(501, "en", null).andExpect(jsonPath("$.when").value("in 5 days"));
        reminder(501, "hi", null).andExpect(jsonPath("$.when").value("5 दिन में"));
        clock.now = Instant.parse("2026-10-19T06:00:00Z");
        reminder(501, "en", null).andExpect(jsonPath("$.when").value("tomorrow"));
        reminder(501, "hi", null).andExpect(jsonPath("$.when").value("कल"));
    }

    @Test
    void todayMeansTodayInIndiaNotOnTheServer() throws Exception {
        clock.now = Instant.parse("2026-10-19T20:00:00Z");   // still the 19th in UTC, already 01:30 on the 20th in India
        reminder(501, "en", null).andExpect(jsonPath("$.when").value("today"));
        reminder(501, "hi", null).andExpect(jsonPath("$.when").value("आज"));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Translations as part of the release

Mediqo will support ten languages, and product changes the English text every month. Who translates, how does a new key reach the translators, and what stops a release that has an English sentence but no Tamil one? Decide whether a missing translation should fail the build or fall back to English, and how you would see in production how often patients get a fallback.

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the old reminder, and Java's three-digit grouping.
2.  Write the bundles as whole sentences, and a test that keeps them complete.
3.  Choose the language with `Locale.lookup`; format the date and amount for it.
4.  Turn off the fallback to the server's locale, and test it with the server's locale set to Hindi.

## Design alternatives and trade-offs

| Approach                                      | What it costs                                                                                                     | Verdict             |
|-----------------------------------------------|-------------------------------------------------------------------------------------------------------------------|---------------------|
| Whole sentences in bundles, with placeholders | A translator per language; a test that keys stay in step.                                                         | Chosen              |
| Translated fragments joined in code           | Word order is English in every language.                                                                          | The trap            |
| `NumberFormat` for `en-IN`                    | ₹123,456.50: grouped in threes.                                                                                   | Wrong for lakhs     |
| ICU4J for numbers, plurals and dates          | A large dependency; correct for many more locales and plural rules.                                               | When languages grow |
| Spring's `LocaleResolver`                     | Reads `Accept-Language` for every request; here the patient's preference also matters, so the choice is explicit. | For simpler cases   |
| Texts in a database table                     | Translators can edit without a release; needs its own completeness checks.                                        | Later               |

## Database design

None in this station. If texts move to a table: `message_text(key, language, text)` with a primary key on `(key, language)`, and a check before release that every key has a row for every supported language.

# 3 · Go deeper: Production

Translation quality  
Texts in a health product are reviewed by a native speaker, and ideally by someone medical. The Hindi here is demo text.

SMS length  
Hindi in an SMS uses Unicode encoding: 70 characters fit in one message instead of 160, so a long reminder is sent as several parts.

Server locale  
Containers often run with `C` or `en_US`; developers' laptops may not. With `fallback-to-system-locale: false`, the fallback does not change between them.

Missing translations  
`requestedLanguage` next to `language` lets a dashboard count fallbacks per language, which says which translation to add next.

# 3 · Go deeper: Interview

## Interview takeaways

Why not concatenate translated words?

Languages differ in word order, endings and agreement. Translators need the whole sentence with placeholders, and decide where each value goes.

How does Spring pick a message for a locale?

MessageSource looks for the most specific bundle (messages_hi_IN, then messages_hi), then the default messages.properties. With fallbackToSystemLocale on, it tries the server's locale before the default.

How do you read Accept-Language correctly?

Parse it into weighted ranges (Locale.LanguageRange.parse) and match against the supported list (Locale.lookup or Locale.filter). Treat a malformed header as no preference.

Why doesn't NumberFormat for en-IN give lakh grouping?

DecimalFormat supports a single grouping size, so it groups in threes. ICU4J or a small custom formatter is needed for 1,23,456.

How do you keep translations complete?

A test that every key in the default bundle exists in every other bundle with the same placeholders, run on every build.

## Self-check rubric

| Area        | Meets the bar                         | Above the bar                                             |
|-------------|---------------------------------------|-----------------------------------------------------------|
| Correctness | All 12 tests pass.                    | You added a language and its test caught a missing key.   |
| Messages    | Whole sentences with placeholders.    | Plural or choice formats instead of `if`/`else`.          |
| Locales     | Accept-Language with weights.         | Why the server's own locale must not decide the fallback. |
| Explanation | Why `₹123,456.50` is wrong for India. | When to reach for ICU4J.                                  |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any user-facing text:

- Is every sentence one message, or is it assembled from pieces?
- Are dates, numbers and money formatted for the reader's locale?
- What language does a user get when we lack theirs, and does it depend on the server?
- Does a test fail when a translation is missing?
