# Station 045 plan: Order DTOs with MapStruct

**Problem.** Tiffino's hand-written entity/DTO mapping was 600 lines. delivery_instructions was added to the table,
the entity, the request and the response in March, never to the mapper: it compiled, and the instructions were dropped.

**Endpoints.** `POST /orders` {customerName, phone, address{line, city, pincode}, deliveryInstructions?, lines[1..20]
{item, quantity 1-20, unitPricePaise}} 201 + Location, OrderResponse {id, customerName, phone masked ******NNNN,
address, deliveryInstructions, lines[{…, linePaise}], totalPaise, status}; `GET /orders/{id}` 200/404; 400 bad body or
unknown field (a client cannot send totalPaise).

**Code.** @Mapper(componentModel spring, unmappedTargetPolicy ERROR): request->entity (id, status, totalPaise ignored on
purpose), line, address, @AfterMapping linkLines, entity->response with @Named maskPhone and an expression for linePaise.
Entities: Order (@Embedded Address, @OneToMany lines cascade ALL), OrderLine. Service computes the total.

**Found while building.** (1) MapStruct does not see package-private setters: the generated toEntity filled only the
list and reported nothing, so the ERROR policy did not help; setters are public, and a javac test proves the
behaviour. (2) Hibernate's validate caught SMALLINT vs int for quantity; the column is INT. (3) defaultValue "0" for a
long needs "0L".

**Trap.** `HandWrittenMappingTrapTest`: the old mapper drops the instructions both ways; MapStruct keeps them; javac
with the processor fails a mapper missing a field ("Unmapped target property"); a package-private setter compiles
silently and is not mapped. Mutations: lines not linked -> 4 red; instructions ignored -> 2; phone not masked -> 1;
totalPaise not declared -> compilation error.

**Practice.** 1: a tip across migration, entity, DTOs and total. 2: a kitchen ticket mapping. Design: MapStruct vs
hand-written vs no DTO for internal services.
