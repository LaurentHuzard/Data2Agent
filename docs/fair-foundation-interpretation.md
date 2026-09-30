# FAIR Foundation interpretation: assessment design

The [FAIR Guiding Principles](https://www.gofair.foundation/fair-principles)
name 15 items. The [GO FAIR Foundation interpretations](https://www.gofair.foundation/interpretations)
explain what evidence a machine-actionable implementation should seek. This
document maps each item to a Data2Agent assessment question. MCP now exposes
all 15 through `list_fair_principles`, `get_fair_principle`, and
`assess_fair_principles`. `get_fair_recommendations` exposes prioritized local
finding repairs. The assessment tool reports local diagnostic results,
observed local gaps, and an `evidence_plan` with one concrete action per
unverified requirement. Its principle-level result stays `unknown` until every
requirement is verified. An opt-in public DOI probe can record a scoped HTTP
observation, but cannot by itself verify the resource identity or A1.1.
Each item exposes its own acceptance criteria and labels every evidence origin
as local, live-publication, external document, reviewed assertion, or validator
report. The output contract is
[`schemas/fair-foundation-assessment.schema.json`](../schemas/fair-foundation-assessment.schema.json).
The Foundation's interpretations guide implementation choices; they do not
prescribe one technology stack.

`observed_local_gaps` contains only failed narrow checks and cites their
evidence. An empty list does not mean the dataset satisfies the principle.
Each `evidence_plan` entry starts at `not_verified`: that means the system has
not established the requirement, not that the requirement is absent from the
dataset. Partial live observations carry their source and observation time.
For an unpublished dataset, call `assess_fair_principles(unpublished=true)`;
publication-dependent requirements become `pending_publication` and retain
their release-time verification action. This is a user-declared workflow state,
not a machine-verified fact or a FAIR verdict. Vocabulary resolution and domain
validation remain actionable before publication.
The `recommendations` list starts with repairs for observed local gaps, then
gives a concrete way to supply and check every unverified item.

## Assessment contract for the FAIR agent

For every item, return a separate result, the precise question assessed, the
scope (local package, published record, or policy), evidence with source and
observation time for live checks, a reason for `fail` or `unknown`, and actions that
would produce the missing evidence. Never turn a successful proxy check into a
pass for the broader principle. Distinguish `not observed`, `not checked`, and
`checked but absent`. A local package alone usually cannot establish service
behavior, identifier persistence, or future preservation.

The existing `run_fair_check` results are *narrow checks*, not principle-level
verdicts. In particular, a local file or keyword is not proof of repository
indexing, a semantically qualified link, a usable licence, or standard
conformance. Preserve the existing rule IDs as historical checks if they are
renamed or superseded; do not silently change what an existing result means.

| Item and interpretation | Evidence to seek for a principle-level assessment | Current rule and gap | Recommendation when evidence is absent |
| --- | --- | --- | --- |
| [F1](https://www.gofair.foundation/f1): Both data and metadata need globally unique identifiers, an issuer commitment to persistence, and predictable machine resolution. | Identify the exact object each identifier denotes; validate scheme and issuer, resolve it to the expected object/metadata, and record the issuer's persistence policy. Check data and metadata separately. | `F1-PID-METADATA` finds identifier-shaped strings; `F1-PID-RESOLVABLE` always returns unknown. Neither proves object identity, issuer policy, or metadata identity. | Assign identifiers through a suitable service; record object-to-identifier links and the service's persistence policy; verify resolution. |
| [F2](https://www.gofair.foundation/f2): Rich descriptive metadata lets an unfamiliar user or machine discover the resource by attributes. Citation fields are a baseline; domain descriptors improve search. | Verify nonempty, meaningful title, creator, publisher, publication date and identifier where relevant; test descriptive and domain fields against a declared metadata schema and discovery use cases. | `F2-METADATA-PRESENT` establishes only recognition of a metadata file. | Add citation and domain search attributes with curator-approved values; validate them against the chosen schema. |
| [F3](https://www.gofair.foundation/f3): Metadata must explicitly identify the resource it describes through an unambiguous, known relationship; the link should persist even if metadata and data are separate. | Parse a known predicate or schema field whose value is the data object's identifier; verify it denotes the assessed resource. Check reciprocal discovery where supported. | `F3-METADATA-LINKS-DATA` searches for filenames in metadata text, which does not establish an identifier relation. | Add a typed metadata-to-data identifier link using the selected schema. |
| [F4](https://www.gofair.foundation/f4): The metadata or data must actually be indexed by a searchable service, discoverable through metadata attributes or the object's identifier. | Identify the registry and query it by the identifier and representative descriptive attributes; record returned record identity, query, time and endpoint. | `F4-METADATA-MACHINE-READABLE` detects structured metadata, not registration or search. | Deposit/index the metadata in a searchable registry and verify discovery. |
| [A1](https://www.gofair.foundation/a1): A standardized, predictable protocol uses the identifier to lead to the resource or a clear access procedure. Restricted access can still meet the principle. | Resolve the identifier; follow documented protocol responses to the resource or an unambiguous request procedure, including permitted authenticated access. Record response chain and access conditions. | `A1-RETRIEVAL-PROTOCOL` always returns unknown. | Publish a stable landing/access route and test it from the intended requester context. |
| [A1.1](https://www.gofair.foundation/a1-1): The access protocol itself must be open, free to specify and universally implementable; this is distinct from whether the data are free to use. | Identify the actual communication protocol and its accessible specification; check that implementation is not restricted to one vendor or group. | No rule. | Offer access via a documented open protocol, such as standard HTTP, where appropriate. |
| [A1.2](https://www.gofair.foundation/a1-2): Where access restrictions apply, the mechanism must support explicit authentication and authorization for human or machine requesters. FAIR does not require all data to be open. | Determine whether restrictions apply; if so, inspect documented requester identity, authorization conditions and access flow. A public resource may have no need to exercise an authentication flow; record why. | No rule. | Document and test the access procedure and permitted uses with the data controller. |
| [A2](https://www.gofair.foundation/a2): Usable metadata must remain discoverable and accessible after the data disappear. | Inspect the repository's metadata preservation policy and stable metadata identifier/access route; where possible test a withdrawn or tombstoned record. A live dataset alone cannot prove future behavior. | No rule. | Choose a repository with a stated retention/tombstone policy and persistent metadata records. |
| [I1](https://www.gofair.foundation/i1): Knowledge representation requires a shared, formal language with machine-interpretable entities and relationships. A syntactically open table does not by itself convey meaning. | Identify the representation language and validate a parser/schema/model that exposes entities, predicates, and their meanings; distinguish syntax from semantic interpretation. | `I1-DATA-FORMATS-OPEN` tests a format allowlist; CSV/JSON can pass without knowledge representation. | Publish semantic descriptions or a representation in a suitable formal language, while retaining useful source formats. |
| [I2](https://www.gofair.foundation/i2): Terms must denote defined concepts unambiguously, and the vocabularies themselves should be findable, accessible, interoperable and reusable. | Extract actual term identifiers and predicates, resolve their definitions, validate term use in context, and inspect vocabulary version/licence/governance. | `I2-VOCABULARY-REFERENCED` finds namespace text; an empty `@context` no longer passes, but the check still does not validate term use or vocabulary FAIRness. | Select a maintained vocabulary with the domain curator; map fields to defined terms and validate the mappings. |
| [I3](https://www.gofair.foundation/i3): References to other resources need a persistent target identifier *and* a named, interpretable relationship. | Parse typed links to other data or metadata; verify relation predicate, target identity and resolution where available. Separate metadata-to-subject links (F3) from links to other resources. | No rule. | Add qualified links such as version, derivation or related-resource relations using a suitable model. |
| [R1](https://www.gofair.foundation/r1): Rich metadata lets users judge fitness for a specific reuse task, beyond finding the resource. Accuracy and relevance depend on domain and intended use. | Assess operational context such as methods, units, populations, conditions, quality, limitations and processing against a declared domain profile and curator review. Record which reuse questions the metadata can answer. | No rule; F2 presence and the R1 subchecks do not establish this. | Add domain-specific context and limitations that prospective users need to evaluate reuse. |
| [R1.1](https://www.gofair.foundation/r1-1): Data and metadata each need clear, accessible usage terms; their licences can differ, and restrictions do not automatically mean failure. | Verify a nonempty, retrievable licence or explicit terms; determine which resource it applies to, allowed uses, and any conflicts among components. | `R1.1-LICENCE-DECLARED` now rejects empty values, but does not verify accessibility, scope or compatibility. | Ask the rights holder to choose terms for data and metadata; make the terms discoverable and check their scope. |
| [R1.2](https://www.gofair.foundation/r1-2): Detailed provenance describes how, why, by whom and under what conditions the resource was produced, plus source data, ownership/credit and later processing. | Validate a lineage record with responsible parties, source materials, methods, conditions and transformations, using a declared provenance model where possible. | `R1.2-PROVENANCE-DECLARED` now rejects empty values but checks only that some origin-related field is declared. | Capture the production and processing history with the producer, using explicit links to source objects. |
| [R1.3](https://www.gofair.foundation/r1-3): Follow standards and minimum-information practices relevant to the actual research community; meeting a filename convention is not conformance. | Identify the domain and its chosen standard/version; validate required fields and applicable data/metadata constraints; record justified exceptions. | `R1.3-COMMUNITY-STANDARD` recognizes a convention without conformance or domain suitability. `R1.3-MISSING-VALUES-DECLARED` is a useful additional data-quality check, not a full R1.3 verdict. | Select a community standard with domain experts and run its validator; document missing information and exceptions. |

## Implementation sequence

1. Every Foundation item now has an addressable assessment record while the
   current narrow checks retain their existing IDs. `assess_fair_principles`
   accepts an optional item ID; a separate MCP tool per item is unnecessary.
2. Return `unknown` for principle-level items until their required evidence can
   actually be checked. The bounded opt-in HTTP probe establishes only the
   protocol evidence it observes, not indexing, retention, permissions,
   semantic conformance, or domain suitability.
3. Add validated evidence inputs for registry queries, preservation policies,
   and access conditions, with endpoint, timestamp and response. Capture
   authorization safely without storing credentials in assessment artifacts.
4. Add schema, vocabulary and domain validation only after a domain profile has
   been selected. Make human judgments visible as reviewed evidence, not as
   deterministic machine observations.
5. Generate recommendations from the exact missing evidence for each item.
   Do not recommend remedial work for `not_applicable`, and do not promise that
   following a recommendation will produce a pass without reassessment.
