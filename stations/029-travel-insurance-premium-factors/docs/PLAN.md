# Station 029 plan: Travel insurance premium factors

**Problem.** Bimaly's premium is one giant class; every new risk factor means editing it. A first split into beans
broke in two ways: one PremiumFactor injected where several exist (NoUniqueBeanDefinitionException, then a @Primary
"fix" that quotes with one factor), and order left to classpath scanning, which changes the price.

**Endpoint.** `POST /premium-quotes` {age, destination, days, adventureSports?} 200 premium (rounded up to the rupee),
per-day figure (nearest rupee) and an ordered breakdown; 422 over 80 (agent only, demo rule); 400 bad fields.

**Data.** No database. `PremiumFactor` beans with @Order: Base 10, DestinationRisk 20, Age 30, AdventureSports 40
(flat, not multiplied by age), Minimum 100. `List<PremiumFactor>` injected sorted. Two `Rounding` beans: @Primary
nearest, @Qualifier("premium") up. @PostConstruct refuses missing or duplicate @Order. Demo rates.

**Trap.** `FactorOrderTrapTest` (ApplicationContextRunner): one-of-several fails to start; @Primary quotes 0;
two orders give 183,875 vs 223,875. Mutations: no @Order -> context fails; adventure before age -> 2 red; calculator
without @Qualifier -> 1 red (48,344 -> 48,300 instead of 48,400).

**Tests.** Trap, `PremiumQuoteContractTest`, `FactorWiringTest` (list order as a subsequence, qualifier vs primary,
stateless singletons, duplicate @Order refused).

**Practice.** 1: pre-existing condition factor (new bean only). 2: campaign discount with @ConditionalOnProperty.
Design: factors from configuration instead of classes.
