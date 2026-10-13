# Station 010 plan: Threaded comment replies

**Problem.** Chaupal stores comments flat; replies showed before their parents, and a recursive tree builder crashed
with StackOverflowError on a 100,000-deep bot thread.

**Endpoint.** `GET /posts/{id}/comment-tree?maxDepth` (default 5, 1-10) → 200 tree (empty list allowed), 400, 404.

**Data.** No database. Post 1: 9 comments stored newest first; post 2: a 100,000-deep chain; post 3: empty.
`ThreadBuilder`: one pass groups by parentId (HashMap), orphans become top level, siblings by createdAt then id,
nesting bounded by maxDepth, `countBelow` iterative (ArrayDeque) for moreReplies; loops are never reached.

**Trap.** Unbounded recursion. `UnboundedRecursionTrapTest`: naive builder -> StackOverflowError on post 2; endpoint
answers with moreReplies 99,997. Mutation: recursive countBelow -> 2 tests red (StackOverflowError).

**Tests.** Trap, `CommentTreeContractTest`, `ThreadBuilderTest` (orphan, loop with timeout, ties, 100k deep, 5k wide).

**Practice.** 1: totalReplies on every node. 2: rootId ("continue this thread"), 404 for another post's comment.
Design: a 2-lakh-comment post.
