# Station 031 plan: Appointment reminders in many languages

**Problem.** Mediqo's reminders were built by gluing translated fragments in English word order, the date was
formatted once in English, and the amount was `paise / 100.0` (123456.5). Hindi-speaking patients got broken
sentences with English months and an unreadable amount.

**Endpoints.** `GET /appointments/{id}/reminder?lang` 200 {appointmentId, language, requestedLanguage, text};
404 unknown appointment; 400 a `lang` that is not a language tag.

**Data.** No database. Two demo appointments in memory (501 Asha prefers Hindi, ₹1,23,456.50; 502 Ravi prefers
English, ₹500.00). `messages.properties` (English, the fallback) and `messages_hi.properties`: one whole sentence per
language with numbered placeholders. `spring.messages.fallback-to-system-locale: false`.

**Language.** `?lang`, then `Accept-Language`, then the patient's preference; matched with `Locale.lookup` against
[en, hi]; no match or a malformed header gives English. Dates: `FormatStyle.LONG` in `<lang>-IN`. Money:
`IndianRupees.format(paise)` (lakh/crore grouping) because `DecimalFormat` has one grouping size.

**Trap.** `ConcatenatedReminderTrapTest`: the old fragments give "123456.5" and "October" in a Hindi sentence; Java's
en-IN currency format gives ₹123,456.50; the real reminder is one Hindi sentence. Mutations while building:
JDK formatter instead of IndianRupees -> 4 red; English dates everywhere -> 5 red; header ignored -> 2 red;
fallback-to-system-locale true -> 1 red.

**Tests.** Trap, `ReminderContractTest` (precedence, fallback, 404, 400, server locale), `MessagesTest` (bundles
complete with the same placeholders, rupee table, matching rules).

**Practice.** 1: Marathi. 2: "today / tomorrow / in N days" with a choice format and a Clock, counted in India.
Design: who translates, and how a missing translation is caught before release.
