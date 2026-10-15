#!/usr/bin/env bash
# Captures real request/response pairs from the running app into docs/captures/.
# Run by tools/build_station.sh --capture (which starts PostgreSQL and the app first). Run from the station folder.
set -euo pipefail
cd docs/captures
# First line: "$ curl" and each argument in single quotes, so the page renderer can split it back exactly.
cap() { name=$1; shift; { printf '$ curl'; printf " '%s'" "${@//\'/\'\\\'\'}"; echo; echo; curl -s -i "$@" | grep -viE "^(date|keep-alive|connection|transfer-encoding):" | tr -d '\r'; echo; } > "$name.txt"; }
B=http://localhost:8080
J="Content-Type: application/json"
cap 01-asha-enrols-in-spring-boot -X POST "$B/courses/1/enrolments" -H "$J" -d '{"studentId":1}'
cap 02-and-in-git-basics -X POST "$B/courses/3/enrolments" -H "$J" -d '{"studentId":1}'
cap 03-rahul-enrols-in-spring-boot -X POST "$B/courses/1/enrolments" -H "$J" -d '{"studentId":2}'
cap 04-asha-has-done-12-lessons -X PATCH "$B/enrolments/1/progress" -H "$J" -d '{"lessonsCompleted":12}'
cap 05-asha-finishes-git -X PATCH "$B/enrolments/2/progress" -H "$J" -d '{"lessonsCompleted":8}'
cap 06-ashas-courses "$B/students/1/courses"
cap 07-enrolled-twice -X POST "$B/courses/1/enrolments" -H "$J" -d '{"studentId":1}'
cap 08-lesson-41-of-40 -X PATCH "$B/enrolments/1/progress" -H "$J" -d '{"lessonsCompleted":41}'
cap 09-no-such-student "$B/students/99/courses"
# The join table itself after the requests above: one row per student and course, with the link's own columns.
docker compose -f ../../compose.yaml exec -T postgres psql -U shikshalab -d shikshalab \
  -c "SELECT id, student_id, course_id, course_lessons, enrolled_on, lessons_completed, completed_on FROM enrolments ORDER BY id" > rows.txt
date '+%-d %b %Y' > date.txt
