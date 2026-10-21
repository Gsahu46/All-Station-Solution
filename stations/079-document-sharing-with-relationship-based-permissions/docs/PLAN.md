# Station 079 plan: Document sharing with relationship-based permissions

**Problem.** Taskloom checked sharing with ad-hoc SQL in 30 places and copied permissions onto each document; a user
removed from a team still opened its documents for a week.

**Endpoints.** HTTP Basic (demo users), stateless. `GET /docs/{id}`: the document and yourAccess (viewer, editor,
owner); no access is 404. `POST /docs/{id}/shares` {subject user:x or team:x, relation viewer|editor}: 201; viewers
403; no access 404; unknown user or team 400. `GET /me/shared-with-me`: documents the user can open but does not own.

**Model.** One table of Zanzibar-style tuples (object, relation, subject[#relation]): team member, folder viewer and
editor, folder and doc parent, doc owner, editor and viewer. Access = strongest relation from {the user and every team
they are in, through teams in teams} to {the doc and every folder above it}: one recursive CTE per check, UNION stops
at cycles. Nothing is copied, so team changes take effect on the next request.

**Database.** documents (id shape, title length); relation_tuples (PK all columns; relations allowed per object type;
subject shape: parent is a folder, others a user or team#member; id shape; one parent; one owner); share_notices
(simulated, same transaction as the share).

**Trap.** `CopiedPermissionsTrapTest`: the old copied ACL keeps asha's access after she leaves the team, misses a
document added to the folder later; with tuples she is out at once, the new document is in, a new team member gets
access, and a document shared with a team follows the team.

**Found while building.** (1) `JdbcClient...query(Integer.class).single()` refuses a null value ("Result value is null
but no null value expected"): `max()` over no rows needs coalesce. (2) Expanding a team share into its current users
(the review version) also misses teams inside the team: neha lost access. (3) No test covered paths without a rule
until the denyAll mutation showed it.

**Mutations.** no nested teams -> 2; no folder inheritance -> 7; viewers may share -> 1; share without transaction ->
1; owned docs listed as shared -> 1; no unknown-subject check -> 1; denyAll -> authenticated() -> 1.

**Review.** Team shares written as one row per current member ("checks need no walk"), viewers may share: 3 of 18 fail.

**Practice.** 1: unshare (DELETE /docs/{id}/shares/{subject}). 2: who has access (Zanzibar's expand) for editors and
owners. 3 (paper): own tables against OpenFGA or SpiceDB, and caching checks safely (Zanzibar's zookies).
