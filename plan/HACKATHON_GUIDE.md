# AMD Developer Hackathon: ACT III — simple guide

> Ye file team ke liye hai. Isme hackathon ke rules aur submission ki list hai, aur ye bhi ki hum kya bana rahe hain.
> Data: [lablab.ai event page](https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii) aur repo ka `context/` folder (Oct 16, 2026 tak).

---

## 1. Hackathon kya hai?

| | |
|---|---|
| **Naam** | AMD Developer Hackathon: ACT III |
| **Organizer** | lablab.ai + AMD |
| **Kab** | Online build: **12-18 October 2026** |
| **Kahan** | Online (lablab.ai + Discord). Italy (Rome, Milan, Imperia) mein onsite bhi hai, par online wale bhi submit kar sakte hain |
| **Team size** | 1 se 6 log (hum 2 hain ✅) |
| **Main goal** | AMD technology se ek **asli business problem** solve karna |

---

## 2. Prizes

| Prize | Amount |
|---|---|
| **AMD prizes** | $5,000 |
| Google prizes | $5,000 |
| Evolus track (Business Agents) | ~€1,011 + plan credits |
| Vibe Generation special prize | AirPods 5 (har member ko) |
| **Total pool** | $17,000+ |

👉 Hamara main target **AMD prize** hai.

---

## 3. Hamara track: Intelligent Industry

**Track ka brief:** factories ko problems jaldi pakadne aur behtar chalne mein madad karo, taaki downtime kam ho, quality aur safety badhe, aur resources sahi use hon.

**Demo mein judges ye dekhna chahte hain:**
- Asli industrial data jaisa input, aur uska useful result (alert, explanation, recommendation ya action)
- Saaf ho ki **kaun use karega** aur **kya improve hoga**

**Acche projects ki pehchaan (official):**
- ✅ Asli manufacturing problem
- ✅ Working product, sirf dashboard ya presentation nahi
- ✅ Results jo operator samajh sake
- ✅ Measurable improvement: time, cost, safety, quality ya efficiency

---

## 4. Sabse zaroori rule: AMD par chalna chahiye

> "AMD is a required technology to be eligible for prizes."

- Project ka **meaningful hissa** AMD par chalna chahiye.
- Wo hissa judges ko dikhaye gaye **working product** mein hona chahiye.
- Allowed: AMD Developer Cloud, AMD Instinct, ROCm, Ryzen AI, Radeon, ya event mein di gayi AMD infrastructure.

**Token Factory (hamara AMD route):**
- Website: `notebooks.amd.com/tokenfactory`
- Card ya billing ki zaroorat nahi
- $100 credit bhi zaroori nahi, sirf Token Factory ki API key chahiye
- Hum isse AI model call karenge (message → constraints)

---

## 5. Participate kaise karein (har member ke liye checklist)

- [ ] lablab.ai par account aur event mein **Enroll**
- [ ] lablab.ai **Discord** join kiya
- [ ] **AMD AI Developer Program** mein signup. Iske bina approval nahi milega ⚠️
- [ ] lablab par **team** banayi aur dono member add hain
- [ ] Token Factory ki API key mil gayi

---

## 6. Kya submit karna hai (checklist)

### 📋 Basic info
- [ ] Project title → **Rehearsal**
- [ ] Short description (1 line)
- [ ] Long description
- [ ] Technology aur category tags

### 📸 Presentation
- [ ] Cover image
- [ ] Video presentation (limit page par nahi likhi; lablab ki general guideline ~5 min hai, form mein check karo)
- [ ] Slide presentation (PDF)

### 💻 App aur code
- [ ] **Public** GitHub repository
- [ ] Demo application platform (jaise Hugging Face Spaces)
- [ ] Application URL, jo bina login ke khule

---

## 7. Judging kaise hogi

| Criteria | Matlab | Hum kaise cover karenge |
|---|---|---|
| **Application of Technology** | Model kitni achhi tarah integrate hua | AMD model message padhta hai; solver, checker aur replay uske output par kaam karte hain |
| **Presentation** | Pitch kitna saaf hai | 4-4.5 min video, live demo, simple slides |
| **Business Value** | Business mein kitna kaam ka | Planner ka time bachta hai, aur galat promise customer tak pahunchne se pehle pakda jaata hai |
| **Originality** | Kitna unique hai | Source-linked constraints, independent checker, "Show a failure" replay |

---

## 8. Deadline ⏰

| Kya | Kab (IST) |
|---|---|
| Event page | "Ends Oct 18, 2026" (time nahi likha) |
| Hamari `context/schedule.txt` | **Oct 18, 3:30 PM** |
| **Hamara target** | **Oct 18, 12 PM tak submit** (safe side) |
| Feature freeze | Oct 17, raat 11 PM |

> Alag pages par alag time likha hai. Isliye last minute ka wait mat karna.

---

## 9. Hum kya bana rahe hain: Rehearsal

**Ek line:** *"Machine band ho gayi? Rehearsal batata hai kaunse orders abhi bhi time par de sakte ho, aur plan lagane se pehle use test karta hai."*

**Kaun use karega:** factory ka production planner ya shift supervisor.

**Flow (5 steps):**

```
1. Planner message likhta hai
   "Mill M2 14:00 tak band hai. J7 ko 16:00 tak ship karna hai."
        ↓
2. AMD AI model message se constraints nikalta hai
   (har constraint ke saath message ke exact shabd; shak ho to insaan se poochta hai)
        ↓
3. Solver 2-3 naye plans banata hai, aur checker har plan verify karta hai
   (koi plan possible na ho to saaf batata hai kyun)
        ↓
4. "Show a failure": plan ko 500 random futures mein chala ke dikhata hai kahan fail ho sakta hai
        ↓
5. Planner approve karta hai → dispatch CSV + decision record download
```

**Tech:** React (UI) + Python FastAPI (backend) + OR-Tools (solver) + AMD Token Factory (AI model).

---

## 10. Kaam kaise baanta hai

Poora phase-wise plan **[PHASES.md](PHASES.md)** mein hai: 15 phases, har phase ki checklist, aur kaun kya karega.

Short mein:

| Phase | Kya |
|---|---|
| 0 | Setup: repo, API key, accounts |
| 1 | Factory timeline screen |
| 2 | AMD se message samajhna |
| 3 | Naye plans banana (solver) |
| 4 | Plans verify karna (checker) |
| 5 | "Show a failure" |
| 6 | Approve + CSV |
| 7 | AMD proof panel (inspector) |
| 8 | Errors aur loading |
| 9 | Accuracy test (15-20 messages) |
| 10 | Deploy (public URL) |
| 11 | README + repo public |
| 12 | Video, slides, cover |
| 13 | GPU replay (sirf time bache to) |
| 14 | Sab jodna + final test + submit |

---

## 11. Ye galtiyan mat karna ❌

- API key GitHub par push karna (`.env` hamesha `.gitignore` mein)
- Repo private chhod dena (public hona **zaroori** hai)
- AMD wala hissa demo mein na dikhana (iske bina prize ke liye eligible nahi)
- Fake ya bina measure kiye numbers bolna ("95% reliable" jaise claims)
- Last 1 ghante mein submit karna
- App URL ka submit ke baad band ho jaana (judging ke time chalna chahiye)

---

## 12. Useful links

- Event page: https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii
- Token Factory: `notebooks.amd.com/tokenfactory` (login chahiye)
- lablab rules: https://lablab.ai/hackathon-rules
- Hamara detailed plan: [PHASES.md](PHASES.md)
- Project decision (kyun ye project chuna): [research/ASTRA_PROJECT_DECISION.md](../research/ASTRA_PROJECT_DECISION.md)
