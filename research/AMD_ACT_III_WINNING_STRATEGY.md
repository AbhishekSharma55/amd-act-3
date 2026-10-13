# AMD Developer Hackathon: ACT III — research and winning strategy

Research date: October 13, 2026. This document precedes project selection.

Team and budget supplied by the participant: two members; **$100 of AMD allocation supplied by the hackathon, plus a maximum of $20 from the participant's pocket**. Project ambition is not capped by team size, effort, or assumed working hours. The external submission deadline and actual service capabilities still determine what can be submitted and demonstrated.

## 1. The strategic conclusion

Our strongest positioning is a distinctive, useful product with a visible result, a measured improvement, and a substantive AMD execution story. It should satisfy three audiences simultaneously: a buyer who understands the value, an engineer who can inspect the implementation, and a judge who can see the evidence quickly.

**Working thesis:** AMD is investing in developer adoption and useful workloads for its open AI stack. A project that could become a credible AMD customer example or reusable developer reference is well aligned with that investment. This is an inference from AMD's published strategy and the event's requirements; it is not an unpublished judging criterion.

For project selection, the most important questions are: what valuable result will we demonstrate; what makes our approach distinct; what evidence will establish improvement; and what precisely runs on AMD? “Uses an LLM,” “has agents,” and “runs on a GPU” are descriptions of components. They do not, by themselves, answer those questions.

The present evidence supports two competitive approaches:

1. A business workflow that converts difficult input into a useful, checked result or action, with meaningful AMD inference or other AMD computation.
2. A technical improvement that produces a demonstrable business benefit on AMD, with a fair baseline and an accessible product around it.

The second approach needs a clear fit to an ACT III challenge. Prior editions accepted infrastructure projects; the current four main challenges focus on business applications. We should verify fit before committing to a pure developer infrastructure submission.

## 2. What this event actually asks for

The event details below are drawn from the participant's files in `context/`, cross-checked against the [official ACT III page](https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii). The local files supply the detailed challenge and prize descriptions.

| Item | Published requirement or description | Consequence for our strategy |
| --- | --- | --- |
| Main objective | Solve a real business problem using AMD technology | Name a specific user, process, and improved outcome |
| Main challenges | Intelligent Industry; Health and Wellbeing; Reinvent Commerce; Create a New Kind of Experience | Give the submission an unmistakable primary challenge fit |
| AMD requirement | A meaningful portion of the workload must run on AMD and appear in the working product shown to judges | Preserve evidence that connects the demo result to actual AMD execution |
| Main rubric | Application of Technology; Presentation; Business Value; Originality | Prepare evidence for all four dimensions |
| Team size | One to six people | Our two-member team is eligible under the published team-size rule |
| Participation | lablab enrollment, Discord, AMD AI Developer Program | Verify administrative approval and team membership separately from building |
| Submission | Descriptions, tags, cover, video, slides, public GitHub repository, application platform and URL | Treat the submission package as part of the product |
| Partner technology | Google and Evolus are optional; main and partner awards can overlap | Add a partner when it improves the product or gives worthwhile award eligibility |

**No ACT III criterion weights, definitive main-prize placement breakdown, or automated benchmark specification were found in the material inspected.** We should not assume equal weights, import ACT II scoring rules, or call the advertised AMD $5,000 pool a $5,000 first-place award.

The general [lablab rulebook](https://lablab.ai/hackathon-rules) supplies a 1–5 rubric. Its stronger levels emphasize functioning artifacts, clarity, commercial potential, and differentiation. That provides useful preparation guidance; the event's numerical aggregation and any special judging process remain unconfirmed.

## 3. Why AMD is hosting this

There is public evidence for developer enablement, software ecosystem investment, and useful deployment. The additional commercial implications below are identified as inference.

| Published evidence | What it establishes | Strategic inference |
| --- | --- | --- |
| AMD's [2025 annual report](https://ir.amd.com/financial-information/sec-filings/content/0000002488-26-000018/amd-20251227.htm) describes investment in ROCm, frameworks, libraries, training and inference, and the developer experience | Software and ecosystem development are part of AMD's corporate AI strategy | Developers who can build and deploy on AMD help turn hardware capability into adoption |
| [Introducing AMD Developer Cloud](https://www.amd.com/en/blogs/2025/introducing-the-amd-developer-cloud.html) explicitly includes evaluation, open-source contribution, native AMD support, events, and hackathons | Cloud access reduces the barrier to trying AMD infrastructure | The hackathon is an acquisition and activation channel for developers |
| [ROCm 10: a simpler path to production](https://www.amd.com/en/blogs/2026/amd-rocm-10-a-simpler-path-to-production-ai-on-amd.html) emphasizes deployment, utilization, validated environments, optimization, and control | AMD's software story extends to operating useful AI workloads | A deployable, inspectable application supports that story more convincingly than an isolated model call |
| AMD's [community inference article](https://www.amd.com/en/developer/resources/technical-articles/2026/kimi-code-in-mxfp4-on-amd-gpus.html) describes community improvements moving through public projects into production | Contributions and public benchmarks can improve the actual stack | Reusable implementations and honest measurements have ecosystem value beyond the contest |
| [AMD AI Playbooks](https://www.amd.com/en/developer/resources/technical-articles/2026/launching-amd-ai-playbooks.html) invites feedback, feature requests, and contributions | Developer experience is improved using real community input | Documenting a reproducible setup, a useful workaround, or a measured optimization makes our work easier to reuse |

The causal chain is straightforward: easier access produces more experimentation; successful experimentation produces working applications and developer familiarity; reusable applications reduce friction for the next developer; sustained application demand can support future hardware adoption. This chain is my interpretation, not a statement that AMD has disclosed ACT III's internal business targets.

That interpretation suggests five things our project can give AMD:

- A credible demonstration of a commercially useful AI workload.
- Evidence that developers can ship using the AMD stack.
- An implementation other developers can reproduce or extend.
- Clear measurements of quality, latency, throughput, or cost.
- Specific, useful feedback about building on the provided infrastructure.

We should make the AMD contribution concrete. Depending on the eventual project, that could be serving an open model, processing multiple inputs efficiently, keeping a substantial pipeline on a GPU, adapting a model, or improving inference operations. We should substantiate the contribution we actually make and distinguish measured results from intended benefits.

## 4. Why the other organizations are involved

**lablab.ai / NativelyAI.** lablab's [sponsorship page](https://lablab.ai/sponsor) offers developer exposure, event visibility, tutorials, and technology-related content. Its model connects technology companies with an active builder community. Successful projects give the platform public examples of what that community produces. Inference: a coherent, complete, easy-to-show submission has value to the organizer as well as to its users.

**Evolus / Codedesign.** Evolus [explains its participation directly](https://evolus.ai/en/blog/evolus-amd-developer-hackathon-lablab): it wants to test what developers build when business-process building blocks are available. The track asks an AMD-hosted open model to drive a real process, using at least two Evolus components. Inference: demonstrate a completed process and the role of those components; a UI that only forwards chat messages leaves much of the partner's proposition unexplored.

**Google / Google DeepMind.** The event lists a Google prize pool. ACT II had Gemma awards, and AMD publishes [support for Gemma on AMD hardware](https://www.amd.com/en/developer/resources/technical-articles/2026/day-0-support-for-gemma-4-on-amd-processors-and-gpus.html). Inference: an excellent open-model application on AMD can support both ecosystems. However, the exact ACT III Google technology and award eligibility are not specified clearly enough to assume that using Gemini, Google hosting, or any Gemma model automatically qualifies.

**Vibe Generation.** The supplied partner brief emphasizes human expertise integrated into actual business processes. Its special-prize criteria cover quantified value, shipping and tool orchestration, originality, taste, and the human-plus-AI workflow. Our response should show how a person uses, reviews, and benefits from the system.

**PwC Italy, IMMENT, and the Italian venues.** Their published participation brings enterprise, startup, and regional innovation context. IMMENT's described incubation awards target Italian teams. The [Milan](https://luma.com/AMDHackathon-Milan) and [Imperia](https://luma.com/AMDHackathon-Imperia) organizer pages emphasize practical building, mentoring, and local connections. It is reasonable to prepare a commercially literate pitch, but there is no evidence that choosing a particular industry or attending in Italy gives an unpublished scoring advantage.

## 5. What previous winners tell us

Winning status is checked using the [ACT I organizer announcement](https://www.linkedin.com/posts/lablab-ai_10770-builders-walked-in-these-teams-activity-7472361155663978496-knnz) and [ACT II organizer announcement](https://www.linkedin.com/posts/lablab-ai_three-tracks-real-amd-hardware-20000-activity-7500512595343405056-jZgl), together with official event results. Technical descriptions and performance numbers below are **team-reported**, sometimes accompanied by public code. I have inspected those descriptions and selected READMEs, but have not reproduced their GPU benchmarks or independently validated their commercial claims.

| Project and result | Evidence available | Lesson for our project |
| --- | --- | --- |
| [Chaos Economy](https://lablab.ai/ai-hackathons/amd-developer/techmavericks/chaos-economy-multi-agent-rl-market-simulator), ACT I AMD + Akash grand prize | A multi-agent market simulation with AMD-hosted training and inference, measured behavior, and a replay interface | Technical novelty becomes legible when judges can observe a concrete behavior and see how it was produced |
| [Intelligence for Existing CCTV Systems](https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-ii/roc-dragon/intelligence-for-existing-cctv-systems), ACT II Unicorn first place | A detection, tracking, cross-camera investigation, and evidence pipeline described as running together on MI300X | Combine a familiar expensive workflow with a visible new capability and a substantive compute story |
| [AgeBand](https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-ii/kiano/ageband), ACT II Unicorn second place | Open-model estimates feed a deterministic policy layer, with confidence and human review | Review boundaries and explicit uncertainty can be part of product differentiation |
| [CacheForge](https://github.com/lucheeseng827/amd-hackathon), ACT II Unicorn third place | A routing control plane; its README reports a controlled real-GPU comparison and separately labels a simulated testbed | A focused technical improvement can be competitive when its benefit is measurable and reproducible |
| [LeAgent](https://lablab.ai/submissions/seswtk4cs6nz2gy2se0dtuf8), ACT II routing-track first place | Heuristics, model routing, local computation, bounded execution, health checks, and metrics | Apply each technique where it helps; orchestration quality includes reliability and economical computation |

Two examples deserve closer attention.

The [CCTV README](https://github.com/CU-DrAgon/rocm-cctv-analysis) describes an operator-facing investigation product, multiple GPU services, containerized deployment, and verification of answers against recorded evidence. Its strength is the connection between infrastructure, an operator's question, and an answer the operator can inspect. We should seek that connection in our own domain, while making our own contribution clear.

CacheForge's README reports a real MI300X comparison using four vLLM workers and 400 requests per mode: mean time to first token fell from 107 to 69 ms, and throughput rose from 20.5 to 25.8 requests per second. It also gives separate simulated-testbed results and distinguishes implemented behavior from a more extensive future architecture. The reusable lesson is the experimental structure: same workload, same infrastructure, one changed policy, reported errors, and a reproduction path. Those particular numbers are not targets for our application.

A useful public comment on Chaos Economy comes from AMD's data-center GPU business development: it praises the new application and the explanation of AMD usage and implementation. That is direct evidence that a clear technology story was appreciated in a prior edition. It is not proof of ACT III weights or a universal formula.

There is an important limit to historical analogy: ACT II's first two tracks used automated scoring, while ACT III currently publishes four product-oriented criteria. Token minimization or a high historical benchmark rank does not establish a winning ACT III product.

## 6. The competition already visible in ACT III

The [live dashboard](https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii/live) showed roughly **5,800 participants, 1,200 teams, and eight public submissions** during this research. Counts changed between retrievals. This is an early snapshot, not a forecast of final entries or a denominator for estimating winning probability. Its visible submission ordering is by community votes.

| Early public entry | Visible proposition | What this means for differentiation |
| --- | --- | --- |
| [DocuSwarm](https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii/yanero-rockstar/docuswarm-parallel-due-diligence-on-amd-gpus) | Parallel document due diligence and AMD throughput reporting | Document upload plus analysis already has competition |
| [Vyson FiscalRAG](https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii/vyson-fiscalrag/vyson-fiscalrag-cited-tax-answers-on-amd-instinct) | Cited tax answers, deterministic calculations, and evaluated retrieval | Citations and a domain-specific corpus are already being claimed |
| [Compressor Maintenance Copilot](https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii/gheware/compressor-maintenance-copilot) | Historical-failure detection connected to an Evolus explanation and work-order flow | Industrial alerts need a distinct task, stronger evidence, or a different valuable action |
| [Industrial Fault Copilot](https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii/industrial-fault-copilot/industrial-fault-copilot) | Manual-grounded troubleshooting and escalation | A maintenance-manual chatbot is already a recognizable category |
| [ForgeSight AI](https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii/amders/forgesight-ai) | Visual inspections, evidence records, and review | Visual inspection plus reporting already has an entrant |
| [Super Secure SYST](https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii/aisupersecuresystv2-3chaliveret/super-secure-syst-v23-6-gas-ai-guardian) | Industrial gas monitoring and workflow automation | Physical sensing and safety automation also appear in the early field |
| [PatientKeeper Retorno](https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii/figueira-ai/patientkeeper-retorno) | Administrative case review, source checking, and disclosed inference failures | Healthcare administration already has a review-focused entrant |
| [Why They Return](https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii/khlab/why-they-return) | Product-return analysis evaluated against labeled reviews | Commerce entrants are already using actual baselines and evaluation data |

The commerce entry reports a 900-review comparison: macro-F1 of 0.737 for its model approach versus 0.606 for keyword rules, with a separately selected product-ranking test. The maintenance entry reports evaluation against four historical leaks and distinguishes real sensor data from synthetic manuals and work orders. These are self-reported results, but their experimental specificity makes “we will evaluate later” a weak competitive position.

**Inference:** manufacturing is closely aligned with the event, but a broad industrial copilot is not automatically original. The early field makes evidence, the precise workflow, and the resulting action especially important. The absence of a category in eight early entries provides no reliable evidence that it will have fewer competitors at the deadline.

We should monitor overlapping projects to clarify our differentiation and compare evidence quality. Community likes, referral points, and visible dashboard position should not be treated as jury scores.

## 7. How to compete across the four criteria

The table below is our preparation framework. It is not an additional official rubric.

| Official criterion | Evidence we should put in front of judges | A common weakness to avoid |
| --- | --- | --- |
| Application of Technology | A working flow; reasoned model choices; substantive AMD execution; inspectable code; reproducible evaluation; visible handling of failures | An impressive architecture diagram whose claimed behavior is not demonstrated |
| Business Value | A named user and buyer; an expensive or frequent task; a measured improvement; realistic operating costs; a plausible adoption path | A large market estimate without evidence that this task matters to a buyer |
| Originality | A specific difference from manual work, a general AI assistant, and existing specialist products; a demonstration of that difference | Rebranding a common workflow without adding a valuable capability |
| Presentation | A clear opening, early product interaction, evidence of the result, an understandable AMD contribution, and concise commercial reasoning | Explaining components for several minutes before showing a useful result |

Our internal standard should be a credible strong showing in every dimension and a memorable exceptional showing in at least one. Improving an obvious weak dimension may matter more than adding another advanced technique to an already impressive component.

The [organizer's winning guide](https://lablab.ai/guide/how-to-win-an-ai-hackathon) independently recommends a focused problem, a working deployed demo, clear value, and a concise pitch. Its generic guidance includes illustrative APIs and timeboxes. For this event, the mandatory AMD execution requirement and our actual ambition take precedence over those generic examples.

## 8. Project-selection principles before ideation

We have not selected a project. Before selecting one, each serious candidate should explain:

1. **The specific valuable result.** Name the role, task, and output or action. A broad industry is insufficient.
2. **The reason current approaches fail.** Determine whether the gap is missing context, unstructured input, cross-system work, verification, responsiveness, or economics.
3. **The distinctive contribution.** State precisely what we will build beyond the model and standard platform components.
4. **The evidence opportunity.** Identify data, labels, a fair baseline, and a repeatable experiment that can establish improvement.
5. **The AMD contribution.** Name the workload and the evidence that it runs on approved infrastructure.
6. **The buyer and adoption path.** Explain how a real organization would begin using it and what it would pay for.
7. **The financial feasibility.** Fit paid dependencies within $20 and the AMD workload within the supplied allocation, accounting for ongoing judging access.
8. **The memorable demonstration.** Identify the moment a judge can directly observe the distinctive capability.

Team size and effort are not elimination criteria. Ambitious ideas remain candidates. We should reject an idea when its essential evidence or deployment depends on an unavailable service, exceeds the budget, fails a rule, or rests on an untestable claim.

The most useful selection advantage is access to credible evidence: relevant data, a real user's description of the task, a trusted evaluator, or a measurable technical baseline. An ambitious domain without that evidence may be less competitive than a familiar domain with a demonstrable new capability.

## 9. Building a convincing proof

Define the experiment when defining the product. This makes later results interpretable and prevents presentation claims from outrunning what we measured.

For a business application, compare our approach against the actual alternative: a manual workflow, an existing tool, rules, or a general model with the same inputs. The baseline should be competent enough to be informative. For an infrastructure improvement, hold hardware, workload, model, output requirements, and load constant when comparing configurations.

Our evaluation should separate development examples from held-out cases. If cases are synthetic, label them and explain their construction. If examples come from a public dataset, preserve the source and its usage conditions. Include at least one difficult case and one case that should be handed to a human or rejected.

Useful measurements depend on the product:

| Product behavior | Quality measure | Operational measure |
| --- | --- | --- |
| Extracts or reconciles documents | Correct fields, correct reconciliation, unsupported outputs | Time per completed case, review time, cost per successful case |
| Produces evidence-based answers | Correct answer, source support, appropriate abstention | Latency, user correction burden, model-call cost |
| Detects faults or defects | Precision/recall, false alerts, measured lead time where supported | Processing throughput, inspection time, operator workload |
| Predicts demand or risk | Error against an appropriate statistical baseline | Decision usefulness, runtime, input freshness |
| Generates adaptive experiences | Consistency, user preference, audience-specific behavior | Cost per usable output, rendering latency |
| Improves inference infrastructure | Correctness, error rate, equivalent output quality | Throughput, time to first token, tail latency, GPU use |

Use **cost per successful outcome** when retries, discarded outputs, or review change the economics. Throughput without adequate quality can misrepresent usefulness. Report sample counts and failure counts alongside headline metrics.

Keep three categories distinct in the pitch:

- **Measured:** a result actually observed using a documented test.
- **Modeled:** an economic estimate using disclosed assumptions.
- **Planned:** a future capability or experiment.

For example, faster analysis in a benchmark does not establish a measured reduction in factory downtime, patient risk, or product-return rates. Those outcomes need their own validation. We can still provide a transparent economic estimate.

A simple business calculation is: cases per month × measured minutes saved per case × relevant hourly cost, minus inference, platform, and additional review costs. Label the labor-cost and volume assumptions, distinguish time released from cash actually saved, and avoid adding overlapping benefits twice.

## 10. Making AMD usage inspectable

Use an architecture diagram that follows the demonstrated request from input to result, with the AMD stage identified. Then provide a concrete run record.

For self-hosted execution, that record can include the accelerator, software/container versions, model identifier, benchmark configuration, timestamps, and trace from application request to model response. For a managed AMD-backed API, use the service's official infrastructure description and request logs. Claim the level of hardware visibility we actually have.

A strong application can show its AMD component in the result inspector or a concise technical view. We should make that accessible to a judge without forcing end users to understand infrastructure.

If we claim an optimization, isolate it with a comparison. Serial versus batched execution on the same AMD environment may be a useful comparison for some workloads. If we claim a memory-capacity benefit, show the actual model/pipeline footprint. If we claim deployment control, show the actual data path and dependencies.

Open weights alone do not establish privacy. An Evolus application can still send documents to managed extraction or indexing stages. Any eventual privacy proposition must match the full architecture, not just the inference endpoint.

## 11. Partner awards and prize strategy

The participant's reward file and current event page advertise $17,000+ total value: $5,000 from AMD, $5,000 from Google, Evolus subscriptions/credits, a Vibe Generation device prize, and Italian-team incubation opportunities. The headline combines different forms of value. Our goal is the main AMD competitive result; a partner award is an additional opportunity.

The main AMD pool does not currently establish which placement receives what amount or whether awards are divided by challenge. The Google pool lacks a sufficiently detailed ACT III eligibility specification. Evolus explicitly provides plans and credits, with no cash alternative, under its [event conditions](https://evolus.ai/en/hackathon-conditions).

We should pursue overlapping awards when a relevant model or platform improves the same product. Before relying on eligibility, confirm the qualifying technology, required opt-in, and artifact requirements. The expected benefit must justify integration cost and any effect on the main demo's reliability or clarity.

ACT II's organizer search-indexed [Google award announcement](https://se.linkedin.com/company/lablab-ai) says its first-track Gemma award was not made because no first-track submission applied. This supports checking application mechanics explicitly. It does not establish that an ACT III category will be less competitive; the company feed is dynamic and its announcement should be reconfirmed if we rely on that historical detail.

For Evolus, using a workflow and a knowledge library is a possible qualifying pair, but we should choose components for their role in the eventual process. Workspace configuration and usage are reviewed, so preserve the actual integration and execution evidence.

The Google/Gemma overlap is worth investigating once we know the task. Model quality, supported features, and official eligibility should decide the model choice. We should not sacrifice the main result merely to attach another sponsor name.

## 12. Important inconsistencies and unresolved requirements

### Submission timing

| Source | Time or date found | What it appears to describe |
| --- | --- | --- |
| Participant's `context/schedule.txt`, also the main page's embedded custom schedule | October 18, 12:00 CEST = **10:00 UTC = 3:30 PM IST** | Explicitly labeled submission deadline |
| Official [Milan](https://luma.com/AMDHackathon-Milan) and [Imperia](https://luma.com/AMDHackathon-Imperia) venue pages | October 18, 16:00 local = **14:00 UTC = 7:30 PM IST** | Explicitly labeled submission deadline on venue agendas |
| Current public event data and structured event metadata | `endAt` / event end: October 18, **15:00 UTC = 8:30 PM IST** | Overall event end; this is not sufficient to establish a submission cutoff |
| A generic timeline row in the main page's public data | End: October 17, **17:00 UTC = 10:30 PM IST** | Conflicts with the actual event end and the current custom schedule; likely an older timeline entry, but that explanation is unconfirmed |
| Live dashboard description | Online build October 12–17 | Also conflicts with the main page's October 12–18 description |

The actual public `endAt` field is Sunday, October 18. The Saturday timestamp belongs to a timeline row; it must not be presented as a verified backend submission cutoff. The explicit Sunday deadlines still disagree. **Our recommended operational target is a complete, submitted entry by Saturday, October 17, 6:00 PM IST**, pending organizer clarification. That is our protective target, not an official deadline. An organizer-confirmed cutoff can replace the uncertainty.

### Evolus model route and workspace

The lablab event brief specifies an owned vLLM endpoint on AMD Developer Cloud. The [Evolus event article](https://evolus.ai/en/blog/evolus-amd-developer-hackathon-lablab) says its track accepts an AMD-hosted open model through Fireworks or owned vLLM. The [developer instructions](https://evolus.ai/en/developers) support those connection routes. Platform compatibility and prize eligibility are separate questions. Confirm whether Token Factory also satisfies the track requirement before relying on it.

The main event page describes activation by a kickoff code and an October 31 expiry; Evolus's [current event page](https://evolus.ai/en/hackathon) instead provides an event join link and November 15 expiry. Follow the current partner instructions to obtain an event workspace and confirm track eligibility with the organizers. The event link is `https://app.evolus.ai/join/AMDACT3`.

The partner's event conditions require workspace users to be at least 18. They prohibit uploading other people's personal data, including health data, and allow own or test data. These are material requirements if we choose a health or people-related process. The conditions also make clear that the prize rules remain on lablab.

### Other open points

- Exact AMD awards, challenge allocation, judging stages, numerical weights, and tie-breaking.
- Whether online entrants share all main/partner award eligibility with on-site entrants, and how any live judging is handled remotely.
- Exact Google qualifying models/technologies and application mechanics.
- Whether container submission is universal: it is explicit in the Evolus brief but not uniformly detailed elsewhere in the main requirements.
- Whether there are required automated endpoints, image architecture, authentication instructions, or runtime limits for ACT III.
- How pre-existing scaffolds must be disclosed and what new work the event requires.
- How long judges need the live AMD endpoint to stay available after submission.

The shared [submission guide](https://lablab.ai/delivering-your-hackathon-solution) currently contains an IBM Bob report reference associated with another event. No corresponding ACT III requirement was found. Use the ACT III requirements as the primary guide and resolve any form-specific additions with the organizer.

## 13. Budget plan

**Confirmed participant constraint: $100 event-supplied AMD allocation + $20 personal spending.** No money has been spent during this research.

The event's supplied FAQ says Token Factory access does not require the $100 credit or a payment card. That can make an API-driven AMD application possible without spending the GPU allocation. Direct GPU access remains useful when we need custom serving, adaptation, telemetry, or an optimization experiment.

| Resource | Proposed treatment |
| --- | --- |
| Supplied AMD inference access | Use for the actual product when its available models and capabilities fit |
| $100 AMD allocation | Spend on experiments and meaningful AMD computation, preserving enough availability to demonstrate and support judging |
| Evolus event workspace | Use the free event workspace only if it contributes to the process; monitor platform-credit and request limits |
| Application hosting | Prefer a suitable free plan, subject to its actual deployment and availability limits |
| $20 cash | Keep available for a necessary dependency or deployment gap; spending it is not an objective |
| Datasets, services, hardware | Reject paid requirements that exceed the budget unless an existing or event-provided resource covers them |

Do not calculate GPU hours from an old promotional rate. Read the actual allocated environment's credit accounting and price before scheduling expensive runs. Shut down idle chargeable resources when appropriate, preserve run artifacts, and plan judging availability explicitly. Event credit terms and Token Factory model/rate limits were not visible without authentication.

We should choose model capacity from task evidence. Bigger models, more calls, and more agents are justified when they improve the outcome enough to warrant their resource use. Financial discipline does not require reducing the ambition of the product.

## 14. What the demo and pitch must establish

The recommended package is a 4–4.5 minute video, a PDF deck, a public repository with usable instructions, and an application judges can access. The general organizer guidelines set a five-minute video maximum; confirm the active form's limits before uploading. See [participation/submission guidelines](https://lablab.ai/ai-articles/hackathon-guidelines).

A proposed video sequence:

| Segment | Evidence conveyed |
| --- | --- |
| First 20–30 seconds | Specific user, costly task, and the result the product delivers |
| Next 90 seconds | A realistic input moving through the working product to an inspectable result or action |
| Next 30–45 seconds | A difficult case and the system's review, rejection, or recovery behavior |
| Next 30–45 seconds | Measured comparison and the actual AMD execution behind it |
| Final 45–60 seconds | Buyer, economics, differentiation, adoption path, and next validation step |

The opening screen should make the task understandable. The product should offer a prepared realistic example plus a way to inspect inputs, sources, and results. If it can also accept a new judge-provided input, that can strengthen confidence in the demonstrated behavior.

The deck should make the evidence easy to locate: problem and user; distinctive capability; demo; evaluation; AMD architecture; competing alternatives; economics and adoption; next steps and team. Keep claims consistent across the video, description, slides, repository, and application.

The README should identify what runs on AMD, how to configure it, how to run the application and evaluation, which data is synthetic, which dependencies are external, and which parts are future work. Preserve environment examples without secrets and provide clear demo access instructions.

Recorded evidence can protect against a later outage, but identify replay versus live execution accurately. A convincing video should be supported by runnable artifacts and an available demo when the rules require one.

## 15. Work sequence after project selection

This sequence is designed to improve evidence and delivery. It does not limit project ambition by assumed team capacity.

1. **Verify access and rules that affect the architecture.** Check AMD inference, direct compute if needed, model capabilities, partner eligibility, and the submission form.
2. **Define the proof and the distinctive behavior.** Agree on baseline, held-out inputs, success measures, and the memorable demonstration.
3. **Establish the full demonstrated flow.** Connect realistic input, AMD computation, checks, and useful output/action. Use early execution to resolve the riskiest technical assumption.
4. **Develop the differentiating capability.** Add the functionality that makes the approach worth choosing over the best available alternative.
5. **Evaluate and improve.** Record failures, quality, operational cost, and the effect of meaningful changes. Keep a repeatable experiment.
6. **Prepare the submission concurrently.** Maintain accurate descriptions, a clear architecture, evaluation artifacts, and a pitch based on what works.
7. **Submit a complete entry before the protective target.** Check every link and uploaded artifact. Further updates should depend on confirmed platform rules.
8. **Support judging.** Keep the necessary endpoint available, preserve credits, and prepare concise answers about evidence, differentiation, limitations, and costs.

## 16. Questions judges should be able to answer from our submission

- Who uses this, who buys it, and what specific problem improves?
- What did the team create beyond the model and platform components?
- What can the product demonstrate that a competent general AI assistant or current tool cannot do as well?
- Which measured result supports that claim, on how many cases, against which baseline?
- What runs on AMD, and how does the demonstrated request prove it?
- What happens with missing, contradictory, or unsupported input?
- Which decisions are automated, and which require a person?
- What does a successful task cost, including retries and review?
- What is already working, and what remains a planned capability?
- Can another developer run the important parts and reproduce the evidence?

## 17. What this research does and does not establish

High confidence: the event requires meaningful AMD use; its current brief favors real business problems; all four stated criteria matter; public past winners include substantive applications and technical contributions; early current entrants already publish evaluations.

Moderate confidence: adoption, reusable examples, ecosystem feedback, and commercially useful workloads explain the sponsors' investment. These inferences are well supported by public sources, but are not a confidential description of judging intentions.

Unresolved: exact deadline enforcement, prize placement structure, ACT III Google eligibility, numerical weights, some partner route requirements, and post-submission hosting duration. They need authoritative clarification, not a guess.

The sample of winners cannot establish a statistical probability of winning or prove that a single ingredient caused a result. Current project descriptions are self-reported and can change. This research provides a basis for making better choices and producing stronger evidence, not a guarantee or a claim that all competing projects have been evaluated.

The next project discussion should begin with the valuable result and the evidence we can produce. We can then compare ambitious candidates using `PROJECT_SELECTION_SCORECARD.md`, resolve the requirements in `ORGANIZER_QUESTIONS.md`, and choose the strongest main-prize proposition.
