# Rehearsal: complete phase plan (feature-wise, independent phases)

> Discussion ke liye banaya gaya plan. Isme code nahi hai, sirf **kya banana hai, kis order mein, aur kaise pata chalega ki done hai**.
> Tech details (JSON format, solver logic) `plan/` folder ki baaki files mein hain. Yahan sirf planning hai.

---

## 1. Ye plan kaise kaam karta hai

### Feature-wise phases
Har phase ek **poora feature** hai: uska backend logic, uska API endpoint, uska UI hissa, uske tests aur uska done check, sab ek saath. Jo phase uthata hai, wahi use shuru se end tak banata hai.

### Har phase independent kaise hai
Har phase ko doosre phase ka sirf **output format** chahiye, asli code nahi. Wo format `plan/03_API_CONTRACT.md` mein fixed hai, aur uske fake (mock) JSON `plan/mocks/` mein ready hain.

Example: "Show a failure" (Phase 5) ko solver ka schedule chahiye. Wo `mocks/solve.json` se le lo, solver (Phase 3) banne ka wait mat karo.

**3 rules jo independence bachaate hain:**
1. API contract koi akela nahi badlega. Badalna ho to dono milke decide karo, aur usi commit mein mock bhi update karo.
2. Har phase pehle mock data par chalega, phir real data par. Mock se real par switch karne ke liye UI mein ek setting rakho (mock mode on/off).
3. Har phase ka apna folder ya files ho, taaki do log ek hi file mein kaam na karein aur merge conflict na aaye.

### Sirf 2 cheezein independent nahi hain (aur ye theek hai)
- **Phase 0 (Foundation):** baaki sab iske upar khade hain. Iska 90% `plan/` folder mein ready hai, bas repo mein copy karna hai (~30-45 min).
- **Phase 14 (Integration + final QA):** ye sab ko jodne wala phase hai, isliye end mein hi hoga.

### Phase list ek nazar mein

| # | Phase | Kya deta hai | Time (approx) | Must ya Nice |
|---|---|---|---|---|
| 0 | Foundation | Repo, contract, mocks, accounts, API key | 45 min | **Must** |
| 1 | Factory view | Fixture load + timeline chart | 2-3 h | **Must** |
| 2 | Message understanding (AMD) | Message → constraints, source highlight, review | 3-4 h | **Must** |
| 3 | Recovery plans | Solver, alternatives, infeasible card | 3-4 h | **Must** |
| 4 | Independent checker | Har schedule ka alag verification | 1.5-2 h | **Must** |
| 5 | Rehearsal ("Show a failure") | Replay, X of N, failing timeline | 2-3 h | **Must** (simple version) |
| 6 | Approval + export | Concessions, CSV, decision record | 2 h | **Must** |
| 7 | Run inspector + run log | AMD proof panel, health | 1.5 h | **Must** (chhota version) |
| 8 | Errors, loading, edge cases | App kabhi crash na ho | 1.5-2 h | **Must** |
| 9 | Evaluation | Labeled messages + 5-8 held-out recovery cases, results table | 2-3 h | Must (chhota) |
| 10 | Deploy + Docker | Public URL | 2 h | **Must** |
| 11 | Repo, README, licenses | Public repo jo chal jaaye | 1.5 h | **Must** |
| 12 | Pitch material | Video, slides, cover, descriptions | 3-4 h | **Must** |
| 13 | GPU replay on AMD | CPU vs GPU comparison | 2-3 h | Nice-to-have |
| 14 | Integration + final QA + submit | Sab jodna, demo run, form submit | 3 h | **Must** |

---

## 2. Time plan (aaj Oct 16, raat 11 baje se)

**Final deadline: Oct 18, 3:30 PM IST** (`context/schedule.txt`). Venue pages par alag time likha hai, isliye **hum Oct 18, 12 PM tak submit kar denge.**

| Slot | Person 1 | Person 2 |
|---|---|---|
| **Oct 16, 11 PM - 12 AM** | Phase 0 (dono saath) | Phase 0 (dono saath) |
| Oct 17, 12 AM - 3 AM | Phase 2 | Phase 1 |
| Oct 17, 9 AM - 1 PM | Phase 3 | Phase 4 → Phase 6 |
| Oct 17, 1 PM - 2 PM | 🔀 **Sync 1:** jo bana hai wo real API se jodo | 🔀 Sync 1 |
| Oct 17, 2 PM - 6 PM | Phase 5 → Phase 7 | Phase 8 → Phase 10 |
| Oct 17, 6 PM - 7 PM | 🔀 **Sync 2:** deployed URL par poora flow | 🔀 Sync 2 |
| Oct 17, 7 PM - 11 PM | Phase 9 → Phase 11 | Phase 12 (slides, cover, script) |
| **Oct 17, 11 PM** | 🔒 **Feature freeze** | 🔒 Feature freeze |
| Oct 18, 8 AM - 11 AM | Phase 14 (QA + bugs) | Phase 12 (video record + edit) |
| **Oct 18, 11 AM - 12 PM** | **Form submit (dono saath)** | |
| Oct 18, 12 PM - 3:30 PM | Sirf buffer: links check, koi naya kaam nahi | |

- Phase 13 (GPU) **sirf tab** karna, jab Sync 2 tak sab must-haves chal rahe hon.
- Agar kuch phase pehle se ban chuke hain, unhe tick karke table chhota kar do.
- Person 1 ya Person 2 koi bhi ho sakta hai. Phases swap karne ho to kar lo, kyunki koi bhi phase kisi doosre ke code par nahi tika.

---

## 3. Phase 0: Foundation (dono saath, ~45 min)

**Goal:** wo common cheezein jo har phase ko chahiye.
**Input:** `plan/` folder. **Output:** repo ready, API key ready.

### 0.1 Accounts aur eligibility
- [ ] Dono members ka **AMD AI Developer Program** signup confirm (screenshot)
- [ ] Dono lablab par enrolled hain, aur ek hi **team** mein hain
- [ ] Discord join kiya hai (announcements ke liye)
- [ ] Track **Intelligent Industry** final hai

### 0.2 AMD Token Factory access
- [ ] `notebooks.amd.com/tokenfactory` par login karke API key lo
- [ ] **Base URL** note karo
- [ ] **Model list** note karo (kaunse models free hain)
- [ ] Rate limits ya daily limit portal par likhi ho to note karo
- [ ] Ek test message bhejo aur jawab aaye (Postman ya curl se, code ki zaroorat nahi)
- [ ] Check karo ki JSON mode (`response_format`) chalta hai ya nahi
- [ ] Key **sirf** password manager ya team chat ke private message mein rakho, repo mein kabhi nahi

### 0.3 Repo structure
- [ ] Folders banao: `backend/`, `frontend/`, `shared/`, `shared/mocks/`, `eval/`, `docs/`
- [ ] `plan/mocks/*.json` ko `shared/mocks/` mein copy karo
- [ ] `plan/mocks/factory.json` ko `shared/fixture.json` mein copy karo
- [ ] `.gitignore` mein ye daalo: `.env`, `node_modules/`, `__pycache__/`, `dist/`, `.venv/`
- [ ] `.env.example` banao: base URL, model name aur key ka **khaali** variable

### 0.4 Team rules decide karo
- [ ] Branch naming: `p1-timeline`, `p2-extract` (phase number + naam)
- [ ] Merge kaun karega aur kab (har Sync par)
- [ ] Ek team chat thread, jismein blockers turant bataye jaayein
- [ ] Mock mode on/off ka naam (ek environment setting) dono ko pata ho

✅ **Done jab:** dono ke paas repo pull ho, mocks `shared/` mein hon, aur ek real AMD call ka jawab aa chuka ho.
⚠️ **AMD call fail ho gayi** to aage mat badho. Pehle wo fix karo, kyunki ye hackathon ki eligibility hai.

---

## 4. Phase 1: Factory view (timeline)

**Goal:** screen par factory ka abhi ka plan dikhe.
**Input:** `shared/fixture.json`. **Output:** `GET /api/factory` endpoint aur Timeline component.
**Kis par depend nahi:** extraction, solver, replay. Kisi par nahi.

### 1a. Data load
- [ ] Backend fixture file padhe aur `GET /api/factory` par de
- [ ] Fixture ka basic check: har job ke saare operations committed schedule mein hain, aur time format sahi hai
- [ ] Fixture galat ho to server start par saaf error aaye

### 1b. Timeline layout
- [ ] Rows = machines (Mill M1, Mill M2, Lathe L3), naam left side par
- [ ] X-axis 08:00 se 20:00, har ghante par tick
- [ ] Shift end (18:00) par line, aur 18:00-20:00 overtime area alag shade mein
- [ ] "Now" (10:00) par vertical line, label ke saath

### 1c. Operation blocks
- [ ] Har job ka apna color (7 jobs, 7 colors jo alag dikhein)
- [ ] Block par label jaise "J7·2" (job + operation number)
- [ ] Hover par tooltip: job, customer, operation, machine, start-end, due time
- [ ] "Now" se pehle shuru hue (frozen) blocks halke/dim dikhein
- [ ] Badle hue blocks (moved/retimed) ke liye outline ka style ready rakho (Phase 3 use karega)

### 1d. Extra markers
- [ ] Outage block (hatched/striped) ka style ready rakho (Phase 2/3 use karega)
- [ ] Har job ka due time marker (chhota flag ya line)
- [ ] Legend: colors aur symbols ka matlab

### 1e. Header
- [ ] Factory naam + **"Synthetic demo data"** label
- [ ] Current time (10:00) dikhe
- [ ] App ka naam aur ek line ki tagline

### 1f. Reusability
- [ ] Timeline ko koi bhi schedule de do, wo draw kare: committed, alternative ya failing scenario. Phase 3 aur 5 isi ko use karenge
- [ ] Ek "highlight" option: kisi operation ko alag dikhana (bottleneck ke liye)

✅ **Done jab:** committed schedule sahi dikhe, aur fixture se 3 random operations ke times haath se match ho jaayein.
🧪 **Edge cases:** bahut chhota operation (label fit na ho), 18:00 ke baad wala operation, ek machine par koi kaam na ho.

---

## 5. Phase 2: Message understanding (AMD wala hissa)

**Goal:** planner ka message AMD model se constraints mein badle, har constraint ka source dikhe, aur shaky cheez par insaan decide kare.
**Input:** fixture (machine aur job ke naam), contract. **Output:** `POST /api/extract`, Message panel, Constraint list.
**Kis par depend nahi:** solver, checker, replay.

### 2a. AMD call
- [ ] Message + machine names/aliases + job IDs + current time model ko bhejo
- [ ] Model ko sirf allowed types bolne ko kaho: machine down, due date, priority, overtime, unsupported
- [ ] Har constraint ke saath **message ke exact shabd** (source span) maango
- [ ] Time na ho to model ko guess nahi karna, khaali chhodna hai
- [ ] Temperature 0
- [ ] Thinking wala model ho to reasoning low rakho (latency kam hogi)
- [ ] Har call ka record: model naam, latency, tokens, raw output

### 2b. Failure handling
- [ ] Timeout ~30 sec
- [ ] Rate limit (429) ya server error par retry, max 3 baar, `Retry-After` follow karo
- [ ] JSON toota hua aaye to ek baar dobara maango
- [ ] Phir bhi fail ho to user ko saaf error: "AMD model abhi respond nahi kar raha, retry karo"
- [ ] Fallback (agar banaya to) par saaf label lage ki ye AMD output nahi hai

### 2c. Validation (model par bharosa nahi, khud check)
- [ ] Machine ka naam ya alias asli machine se match ho ("big mill" → M2)
- [ ] Job ID exist kare
- [ ] Time sahi format mein ho aur din ke andar ho; `until` time `from` ke baad ho
- [ ] Source span sach mein message mein ho (model ne apni taraf se text na banaya ho)
- [ ] Do constraints aapas mein na takrayein (J7 ke do alag due dates)
- [ ] Outage kisi chal rahe kaam ko roke to note jode: "J1 op 2 restart hoga"
- [ ] Outage ka end time na ho to review: "repair time pata nahi", khud koi time mat bharo
- [ ] Unsupported cheez (material shortage) ho to review
- [ ] Har fail check par status `review` aur reason likho

### 2d. Message panel (UI)
- [ ] Bada text box
- [ ] 4 sample buttons: demo message, unknown machine wala, bina time wala, "no overtime today"
- [ ] "Read message" button, call ke dauraan loading state
- [ ] Message badalne par purane constraints aur plans saaf ho jaayein

### 2e. Constraint list (UI)
- [ ] Har constraint ek line mein, plain English mein ("M2 band hai 10:00-14:00")
- [ ] Status icon: ✓ ok, ⚠ review
- [ ] Issues (reasons) constraint ke neeche dikhein
- [ ] Constraint par click karo to message mein uska source text highlight ho
- [ ] Complete ambiguous interpretation par **Accept** / **Reject**; unknown machine, missing time ya contradiction par Accept disabled. Edit/map + backend revalidation karo, ya reject karke corrected message dobara bhejo
- [ ] Origin badge: "AMD model" ya "fallback" (fallback par warning)
- [ ] Jab tak koi non-rejected review item undecided hai ya `blocking_issues` hain, "Find recovery plans" disabled. Backend `accepted` items ko bhi dobara validate kare

✅ **Done jab:** 5 alag messages (demo, alias wala, bina time, ek job ke do facts, off-topic) par sahi constraints ya sahi review aaye, aur UI mein highlight + accept/reject chale.
🧪 **Edge cases:** khaali message, bahut lamba message, Hindi/Hinglish message, "2pm" ya "4 baje" jaise time, "no overtime".

---

## 6. Phase 3: Recovery plans (solver)

**Goal:** accepted constraints se 2-3 alag recovery plans banao, aur koi plan possible na ho to saaf batao kyun.
**Input:** fixture + `mocks/extract.json` ke constraints. **Output:** `POST /api/solve`, Alternative cards, Before/after view.
**Kis par depend nahi:** extraction (mock constraints use karo), checker, replay.

### 3a. Factory rules (solver ko kya maanna hai)
- [ ] Har operation sirf apni eligible machine par, us machine ke time ke hisaab se
- [ ] Ek job ke operations order mein chalein
- [ ] Ek machine par ek waqt mein ek hi kaam
- [ ] "Now" se pehle shuru hua kaam **fix** rahe, use hila nahi sakte
- [ ] Outage se ruka hua kaam restart hoga (beech se nahi)
- [ ] Outage ke time machine par koi kaam nahi
- [ ] Naya kaam "now" ke baad hi shuru ho
- [ ] Shift 18:00 tak; overtime sirf accepted cutoff tak (fixture ka 20:00 upper limit). Policy isse aage nahi badha sakti; solver aur checker dono enforce karein
- [ ] Hard due date ho to plan usse **todega nahi**

### 3b. Accha plan kaisa hoga (objective)
- [ ] Late jobs kam se kam, priority ke hisaab se weight
- [ ] Nayi due date hard ho ya soft, tardiness aur concession dono usi se niklein; hard date ka feasibility bound alag rahe
- [ ] Overtime ka paisa actual occupied machine-minutes / 60 × hourly rate se; har operation ke end ke baad ki khaali window ko dobara count na karo
- [ ] Purane plan se kam se kam badlav (machine change aur time shift)

### 3c. Alternatives
- [ ] Plan A "Keep machines": machine nahi badlegi, overtime chalega
- [ ] Plan B "Re-route": doosri eligible machine use kar sakte hain, overtime nahi
- [ ] Plan C "Re-route + overtime"
- [ ] Do plans bilkul same nikle to ek hi dikhao, saath mein "merged" note
- [ ] Har plan ke KPIs: late jobs (minutes + customer), overtime minutes + cost, kitne operations moved, kitne retimed
- [ ] Har plan ki concessions list: kaunsi cheez insaan ko approve karni padegi

### 3d. Infeasible case
- [ ] Koi plan possible nahi to "INFEASIBLE" + kaunse constraints takra rahe hain
- [ ] Wording: "ye constraints saath mein possible nahi" (sufficient set hai, minimum nahi)
- [ ] Time limit mein jawab na mile to "10 sec mein plan nahi mila", **"impossible" nahi**
- [ ] Concession options: re-route allow karo, overtime allow karo. Hard due relaxation tabhi enable jab server effective constraints aur extra approval concession store/check kar sake; example helper mein ye disabled hai

### 3e. Alternative cards (UI)
- [ ] Har plan ka ek card, KPIs ke saath
- [ ] Checker badge ki jagah (Phase 4 bharega; tab tak mock se)
- [ ] Infeasible ka **red card**, reason ke saath; constraint IDs par click karo to list mein wo constraint highlight ho
- [ ] Card select karne par timeline badle

### 3f. Before/after
- [ ] Purana vs naya plan (upar-neeche ya toggle)
- [ ] Badle hue operations outline mein
- [ ] Moved operation par "M2 → M1" jaisa label

✅ **Done jab:** demo constraints par "Keep machines" infeasible aaye (J7 conflict), "Re-route" mein J7 time par ho aur J2 190 min late ho. Ye numbers `plan/02_DATA_MODEL.md` se match hone chahiye.
🧪 **Edge cases:** koi constraint nahi (plan same rahe), saari machines down, overtime "not allowed", hard due date jo pehle hi nikal chuki ho.

---

## 7. Phase 4: Independent checker

**Goal:** solver se **alag** code jo har plan ko dobara verify kare. Judges ke liye "trust" ka proof yahi hai.
**Input:** fixture + koi bhi schedule (committed, `mocks/solve.json`, ya haath se toda hua). **Output:** checker module, UI badge, approve ke time re-check.
**Kis par depend nahi:** solver. Checker solver ka code import **nahi** karega.

### 4a. Rules jo check honge
- [ ] Har operation exactly ek baar schedule mein hai (missing ya duplicate nahi)
- [ ] Machine eligible hai, aur duration us machine ke hisaab se sahi hai
- [ ] Job ke operations order mein hain
- [ ] Machine par overlap nahi hai
- [ ] Outage ke time machine par kaam nahi hai
- [ ] Fixed (pehle shuru hua) kaam badla nahi
- [ ] Naya kaam "now" se pehle shuru nahi hota
- [ ] Shift ya overtime limit ke baad koi kaam nahi
- [ ] Hard due dates poori hain

### 4b. Output
- [ ] Valid hai ya nahi + **saari** violations ki list, plain English mein (sirf pehli nahi)

### 4c. Kahan use hoga
- [ ] Har alternative ke saath result (Phase 3 card ka badge)
- [ ] Approve se pehle dobara (Phase 6)
- [ ] Run inspector mein (Phase 7)

### 4d. Test set
- [ ] Committed schedule → pass
- [ ] Mock solve schedule → pass
- [ ] 6 jaan-boojhkar tode gaye schedules, har ek apne sahi reason ke saath fail ho: overlap, galat order, outage mein kaam, frozen kaam hilaya, galat machine, hard due miss

✅ **Done jab:** saare 8 test cases expected result dein.

---

## 8. Phase 5: Rehearsal ("Show a failure")

**Goal:** chuna hua plan 500 random "futures" mein chalao (kaam thoda lamba chale, repair late ho), aur ek future dikhao jismein plan fail hota hai.
**Input:** `mocks/solve.json` ka schedule. **Output:** `POST /api/replay`, Replay panel, failing timeline.
**Kis par depend nahi:** solver (mock schedule), extraction.

### 5a. Simulation ke rules (fix rakho, README mein likho)
- [ ] Machine aur order wahi rehte hain; simulation plan ko dobara optimize **nahi** karta
- [ ] Random cheezein: unstarted operation ka full time (0.9x se 1.3x); chal rahe operation ka sirf remaining time random ho. Observed start aur elapsed time fixed, finish kabhi "now" se pehle nahi
- [ ] Operation apne planned start se pehle dispatch nahi hoga; machine free, pichla operation khatam, "now" aur repair ka wait bhi kare
- [ ] Future repair ka end 0-90 min late; already observed repair fixed rahe
- [ ] Khatam ho chuke kaam mein randomness nahi
- [ ] Fixed seed, taaki har baar same result aaye (demo reproducible rahe)

### 5b. Results
- [ ] Har job: "X of 500 scenarios mein time par"
- [ ] Har job ka 90th percentile finish time
- [ ] Failing scenario: sabse zaroori job jo plan mein time par hai par kuch futures mein late; uska sabse bura future
- [ ] Bottleneck: wo operation/machine jiski wajah se late hua
- [ ] Assumptions ki list (spread, repair delay, samples, seed)

### 5c. UI
- [ ] Har job ka bar: "239 of 500" (percentage reliability claim nahi)
- [ ] "Show a failure" button → timeline par failing future draw ho
- [ ] Bottleneck operation highlight ho
- [ ] Ek line ka reason: "J4 17:00 se 61 min late"
- [ ] Assumptions chhote text mein neeche
- [ ] Optional: repair delay ka slider jo replay dobara chalaye (judges ke liye interactive)

✅ **Done jab:** re-route plan par J4 "239 of 500" aaye (mock se match) aur failing timeline dikhe.
🧪 **Edge cases:** zero randomness par result plan jaisa hi aaye, same seed par same result aaye, koi failure na ho to "No failure found in 500 scenarios" dikhe.

---

## 9. Phase 6: Approval + export

**Goal:** planner trade-offs dekh ke approve kare, aur shop floor ke liye CSV + audit record nikle.
**Input:** `mocks/solve.json` ka ek alternative. **Output:** `POST /api/approve`, Approval panel, 2 downloads.
**Kis par depend nahi:** replay, extraction. Checker real na ho to mock "valid" use karo.

### 6a. Backend checks
- [ ] Har solve ko fresh immutable `run_id` do; server fixture, accepted constraints aur alternatives store kare. Purane run expire ho to UI solve dobara karaye
- [ ] Approve request mein sirf run/alternative IDs, approved concession IDs aur approver naam. Schedule, constraints aur replay server store se lo; client replacements reject karo
- [ ] Stored plan par checker **dobara** chalao; fail ho to approve reject (422)
- [ ] Required concessions stored schedule + effective due dates/overtime se dobara nikalo; cached/client concessions list khaali karne se approval bypass na ho
- [ ] Har derived concession tick hua ho; ek bhi missing ho to reject
- [ ] Approver ka naam khaali na ho

### 6b. Dispatch CSV
- [ ] Columns: machine, sequence, job, op, start, end, changed
- [ ] Machine-wise, phir start time ke order mein
- [ ] "changed" values: none / frozen / retimed / moved_from_X / restarted
- [ ] File naam: `dispatch_<run_id>.csv`
- [ ] Excel mein khol ke check karo ki sahi dikh raha hai

### 6c. Decision record (JSON)
- [ ] Kisne approve kiya, kab (timezone ke saath)
- [ ] Original message
- [ ] Accepted constraints, aur jo reject hue unka bhi record
- [ ] Chuna hua plan, concessions, checker result
- [ ] AMD trace (model, latency), replay summary
- [ ] "Synthetic demo data" note
- [ ] File naam: `decision_<run_id>.json`

### 6d. UI
- [ ] Har concession ek checkbox ("J2 190 min late, Birla Valves")
- [ ] Overtime ho to cost dikhe
- [ ] Approver naam ka input
- [ ] Approve button tab tak disabled, jab tak sab tick na ho aur naam na ho
- [ ] Success par: "Approved by … at …" + dono files download
- [ ] Approve ke baad plan "locked" dikhe; naya message daalne par reset

✅ **Done jab:** mock alternative approve ho, CSV Excel mein sahi khule, aur decision record mein saari fields hon.
🧪 **Edge cases:** ek concession untick, client concessions list khaali bheje, stored schedule checker fail, expired run, double click approve.

---

## 10. Phase 7: Run inspector + run log + health

**Goal:** judges ko dikhe ki AMD sach mein kaam kar raha hai, aur har run ka record ho.
**Input:** contract ke trace fields (mock se). **Output:** `GET /api/health`, run log, Inspector drawer.

### 7a. Health
- [ ] AMD key set hai ya nahi (key khud kabhi mat dikhao)
- [ ] Model naam aur host
- [ ] Replay device (CPU ya GPU)

### 7b. Run log
- [ ] Har run ka ID
- [ ] Har step ka record: extract, solve, replay, approve, with time
- [ ] Memory mein rakho (database ki zaroorat nahi), server restart par khaali hona theek hai

### 7c. Inspector panel (UI)
- [ ] Header mein button, side drawer khule
- [ ] AMD: provider, model, host, latency, attempts, tokens
- [ ] Raw model output (collapsible)
- [ ] Validation issues
- [ ] Har plan ka solver status aur time
- [ ] Checker results
- [ ] Replay: device, samples, time
- [ ] "Live run" vs "recorded/mock" ka saaf label

✅ **Done jab:** ek real run ke baad inspector mein asli model naam aur latency dikhe.

---

## 11. Phase 8: Errors, loading, edge cases (robustness)

**Goal:** judge kuch bhi kare, app crash na ho aur har situation mein saaf message dikhe.
**Input:** contract ka error format. Errors mock karke test kar sakte ho. **Output:** error banner, loading states, input checks.

### 8a. Common error format
- [ ] Har backend error ek hi shape mein: code, message, retry ho sakta hai ya nahi
- [ ] Sahi HTTP status codes (400 / 422 / 502 / 504)

### 8b. UI states
- [ ] Har button par loading spinner, aur call ke dauraan button disabled
- [ ] Ek error banner, backend ka message + Retry button
- [ ] Empty states: koi constraint nahi, koi plan nahi, koi failure nahi
- [ ] Double-click protection

### 8c. Input checks
- [ ] Khaali message par button disabled
- [ ] Bahut lamba message limit (jaise 1000 characters)
- [ ] Ajeeb characters ya emoji se crash na ho

### 8d. Network
- [ ] Backend band ho to "server not reachable" dikhe
- [ ] AMD slow ho to "AMD model soch raha hai…" aur 30 sec ke baad timeout message

### 8e. Browser basics
- [ ] Chrome + ek aur browser
- [ ] Laptop screen par sab dikhe (1366px width bhi)
- [ ] Mobile par kam se kam toota hua na dikhe
- [ ] Page title aur favicon

✅ **Done jab:** ye 6 test pass hon: backend band, AMD key galat, khaali message, unknown machine, infeasible plan, double click approve.

---

## 12. Phase 9: Evaluation (measurable evidence)

**Goal:** judges ke "measurable improvement" ke liye asli numbers.
**Input:** extraction contract + 5-8 held-out recovery scenarios. **Output:** `eval/` mein messages, recovery cases, results table, README section.
**Independence:** labeling aur scenarios abhi freeze kar sakte hain. Final extraction run ke liye Phase 2, recovery comparison ke liye solver/checker/replay chahiye.

### 9a. Messages likhna (15-20)
- [ ] Demo jaisa normal message
- [ ] Alias ("big mill", "VMC-2")
- [ ] 12-hour time ("2pm", "4 baje")
- [ ] End time missing
- [ ] Unknown machine
- [ ] Negation ("no overtime today")
- [ ] Ek job ke do updates (contradiction)
- [ ] Out-of-scope (material shortage)
- [ ] Ek message mein 3-4 cheezein
- [ ] Hinglish message

### 9b. Labeling
- [ ] Ek member messages likhe, **doosra** alag se expected answer likhe
- [ ] Jahan dono ka answer alag ho, discuss karke final label tay karo

### 9c. Metrics
- [ ] Poora sahi (complete-change accuracy)
- [ ] **Galat cheez "ok" ho gayi (false acceptance)**: sabse important number
- [ ] Jahan review aana chahiye tha, wahan aaya
- [ ] Latency: median aur max

### 9d. Results
- [ ] Table README mein aur ek slide par
- [ ] Wording: "builder-labeled set of N messages", benchmark nahi
- [ ] Agar 2 models test kiye, to dono ka comparison

### 9e. Time saved (optional, honest)
- [ ] Ek member manually demo scenario reschedule kare, time note karo
- [ ] Phir Rehearsal se, time note karo
- [ ] Label: "builder-run test, 1 person", koi bada claim nahi

### 9f. Chhota recovery comparison (required evidence, bada benchmark nahi)
- [ ] Demo tune karne se pehle 5-8 alag scenarios freeze: outage, due-date update, limited overtime aur infeasible case
- [ ] Same time budget par correct typed input wala CPU CP-SAT optimizer reference rakho; weak strawman se compare nahi
- [ ] Rehearsal replay hidden vs replay shown compare karo; selection rule pehle fix ho (priority jobs ka sampled risk, phir tardiness/cost)
- [ ] Plan choose karne wale seeds aur outcome check karne wale fixed seeds alag rakho
- [ ] Schedule valid hai ya nahi, weighted lateness, occupied overtime/cost, risky promises exposed aur held-out sampled outcomes ki chhoti table
- [ ] Gain na mile to wahi report karo; data aur uncertainty synthetic label ho. AMD ka role message interpretation, replay ka role risk dikhana; CPU optimizer scheduling karta hai

✅ **Done jab:** table repo mein ho aur har number reproduce ho sake.

---

## 13. Phase 10: Deploy + Docker

**Goal:** public URL jahan judge poora demo chala sake.
**Input:** kuch bhi nahi. Pehle "hello world" ya mock-mode app deploy karke pipeline test karo. **Output:** Dockerfile, live URL.

### 10a. Docker
- [ ] Ek container: React build + Python backend jo React ko serve kare
- [ ] Local `docker build` aur `docker run` chale
- [ ] Image chhota ho (dev files aur `node_modules` copy na hon)

### 10b. Hosting (pehli choice: Hugging Face Space, Docker SDK)
- [ ] Space banao, port 7860
- [ ] AMD key **secret** mein daalo, image ya repo mein nahi
- [ ] Deploy ho, aur URL logged-out browser mein khule
- [ ] Check karo ki free Space so jaata hai ya nahi aur jaagne mein kitna time lagta hai
- [ ] Backup plan: koi doosra host ya chhota VM ($10 personal budget tak)

### 10c. Production checks
- [ ] Mock mode **off** ho
- [ ] CORS sahi ho (same domain par ho to zaroorat nahi)
- [ ] Real AMD call deployed URL se chale (local se nahi)
- [ ] Ek baar poora demo deployed URL par

✅ **Done jab:** phone aur laptop dono par logged-out browser se demo chale.

---

## 14. Phase 11: Repo, README, licenses

**Goal:** public repo jo judges khol ke samajh sakein aur chala sakein.
**Input:** kuch nahi. README ka structure abhi bana sakte ho, details baad mein bharo.

### 11a. Repo cleanup
- [ ] `research/sources/` (~19 MB scraped pages) hatao
- [ ] Ye files git history mein bhi hain. Clean history chahiye to naya public repo banao ya history rewrite karo; ye dono milke decide karo
- [ ] Kahin bhi API key nahi, history mein bhi nahi (search karo)
- [ ] `.env.example` hai, `.env` nahi
- [ ] Faltu files hatao (test outputs, `.DS_Store`)

### 11b. README sections
- [ ] 3 line mein kya karta hai + screenshot/GIF
- [ ] Live demo link + video link
- [ ] **What runs on AMD**: model, endpoint, code mein kahan call hota hai
- [ ] Architecture diagram (message → AMD → validation → solver → checker → replay → approval)
- [ ] Kaise chalayein: Docker aur local dev, dono tarike
- [ ] Data notice: sab synthetic ya team-authored
- [ ] Evaluation table (Phase 9)
- [ ] Replay assumptions aur "X of N" ka matlab
- [ ] Limitations: ek din, restart-only, ERP nahi, business numbers unvalidated
- [ ] Team members

### 11c. Licenses
- [ ] Apni LICENSE file (jaise MIT)
- [ ] OR-Tools Apache-2.0 aur model ka license mention karo
- [ ] Koi dataset use kiya to uska license

### 11d. Visibility
- [ ] Repo **public** karo, submit se pehle
- [ ] Logged-out browser mein khol ke check karo

✅ **Done jab:** naya banda sirf README padh ke app chala sake.

---

## 15. Phase 12: Pitch material

**Goal:** video, slides, cover aur descriptions jo 4 judging criteria cover karein.
**Input:** script aur slides abhi likh sakte ho. Screenshots/recording ke liye working app chahiye, warna mock mode ka UI chalega.

### 12a. Demo script
- [ ] `plan/07_DEMO_AND_SUBMISSION.md` ka 10-step script final karo
- [ ] Har step par kya bolna hai, likh lo
- [ ] Har number asli app se dobara check karo

### 12b. Video (4-4.5 min, form mein limit confirm karo)
- [ ] 0:00-0:25 problem aur user
- [ ] 0:25-3:00 live demo
- [ ] 3:00-3:30 evidence (eval table, checker, replay)
- [ ] 3:30-3:55 architecture aur AMD ka hissa
- [ ] 3:55-4:30 business value, limits, next steps
- [ ] 1080p, browser zoom 110-125%, saaf audio
- [ ] Upload (YouTube unlisted ya jo form maange); logged-out browser mein chalta hai, check karo
- [ ] Backup: demo ki ek screen recording alag se rakho

### 12c. Slides (PDF, ~10)
- [ ] Title + pitch line
- [ ] User aur problem
- [ ] Kya karta hai (5 steps)
- [ ] Screenshots: constraints, alternatives, infeasible, failure
- [ ] Architecture + **AMD par kya chalta hai**
- [ ] Evidence slide
- [ ] Business value ("illustrative" label ke saath)
- [ ] Limits, next steps, team

### 12d. Cover image
- [ ] Form mein size/ratio check karo
- [ ] App ka screenshot + naam + tagline

### 12e. Text
- [ ] Short description (1 line)
- [ ] Long description: problem, user, solution, AMD ka use, evidence, limits
- [ ] Tags: AMD, Token Factory, model naam, OR-Tools, FastAPI, React
- [ ] Har jagah same claims ho (video = slides = README = form)

### 12f. Judges ke sawaal
- [ ] `plan/07_DEMO_AND_SUBMISSION.md` ke 6 sawaalon ke 1-line jawab dono ko yaad hon

✅ **Done jab:** saari files ready hon, aur dono ne video ek baar poora dekh liya ho.

---

## 16. Phase 13: GPU replay on AMD (nice-to-have)

**Sirf tab karo, jab Sync 2 tak saare must-haves chal rahe hon.**

- [ ] AMD GPU instance mile aur budget mein ho ($100 credit mein se); kaam khatam hote hi instance band karo
- [ ] Wahi replay, GPU par
- [ ] Same random numbers par CPU aur GPU ka result match ho
- [ ] 1k / 10k / 100k samples par time measure karo (data transfer bhi gino)
- [ ] Jo result aaye, wahi bolo. GPU slow ho to bhi sach likho
- [ ] Inspector mein device "GPU (ROCm)" dikhe

✅ **Done jab:** comparison table README mein ho.
Agar ye nahi hua, to koi problem nahi. AMD ka zaroori hissa (Phase 2) already hai.

---

## 17. Phase 14: Integration + final QA + submit (dono saath)

**Ye phase jaan-boojhkar sab par depend karta hai.**

### 14a. Integration (Sync 1 aur Sync 2 par)
- [ ] Har phase ka mock mode off karke real API se jodo
- [ ] Ek-ek karke merge karo, har merge ke baad poora flow chala ke dekho
- [ ] Contract se koi mismatch mile to dono milke theek karo

### 14b. Full flow test (deployed URL par)
- [ ] Demo message → constraints → plans → failure → approve → CSV
- [ ] Changed message (repair 15:00 tak) par bhi chale; judge apna input daal sakta hai
- [ ] Review wala message (Mill 4) → reject → solve
- [ ] Infeasible case dikhe
- [ ] Inspector mein asli AMD data dikhe

### 14c. Final checks
- [ ] Har number jo video/slides mein hai, app se match ho
- [ ] Mock data kahin "live" bankar na dikhe
- [ ] Key kahin leak nahi hui
- [ ] App URL, repo, video: teeno logged-out browser mein khulein

### 14d. Submit
- [ ] Title, descriptions, track, tags, cover, video, slides, repo URL, app URL, demo platform
- [ ] Submit se pehle doosra member sab check kare
- [ ] **Oct 18, 12 PM tak submit**
- [ ] Submit ke baad confirmation ka screenshot

### 14e. Judging ke time
- [ ] App jaagti rahe (Space so na jaaye), har kuch ghante kholo
- [ ] AMD key ki limit khatam na ho, isliye faltu testing band
- [ ] Discord par organizers ke messages dekhte raho

---

## 18. Discussion mein ye decide karna hai

| # | Sawaal | Options |
|---|---|---|
| 1 | Kaun kaunse phases lega? | Section 2 ki table ek suggestion hai |
| 2 | Kaunsa AMD model? | Phase 0 mein 2 models test karke decide karo |
| 3 | Fallback banana hai? | Haan (label ke saath) ya nahi (sirf error) |
| 4 | Hosting kahan? | Hugging Face Space ya koi aur |
| 5 | Git history clean kaise? | Naya public repo ya history rewrite |
| 6 | Video mein kaun bolega? | Ek member ya dono |
| 7 | GPU replay try karna hai? | Sirf agar Sync 2 tak sab ready ho |
| 8 | Repair-delay slider (Phase 5c) banana hai? | Time ho to haan |
| 9 | Sync ka exact time | Oct 17, 1 PM aur 6 PM, ya jo dono ko suit kare |

## 19. Time kam pade to kya kaatna hai (is order mein)

1. Phase 13 (GPU)
2. Phase 5c ka slider
3. Phase 9e (time saved test)
4. Phase 9: 20 se 10 messages (10 se kam nahi)
5. Phase 7: inspector mein sirf model, latency, checker
6. Phase 3: Plan C hatao, sirf A + B + infeasible rakho

**Kabhi mat kaatna:** AMD extraction (2), review accept/reject (2e), solver + infeasible (3), checker (4), "Show a failure" ka basic version (5), approve + CSV (6), deploy (10), public repo (11), video + slides (12), submit (14).
