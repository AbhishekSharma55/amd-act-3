# Rehearsal — video recording script

Target: approximately 4–4.5 minutes of narration and short pauses; keep the finished video under five minutes. Organizer guidance: https://lablab.ai/ai-articles/hackathon-guidelines. Check the active upload form before submitting.

Read only the quoted paragraphs. Screen directions are not narration. Record one scene per take. Use the public app in Live API mode, with the default 90-minute repair overrun, 500 scenarios and seed 7. Record actual requests and results; shorten waiting footage with a 'Processing wait shortened' label. Record the unknown-machine take in a second tab after finishing the main flow.

Verified demo facts: M2 unavailable 10:00–14:00; J7 hard due 16:00; re-route keeps J7 on time with J2 190 min late; J4 on time 239/500, failure #24. Evidence: deploy/lightsail/verification/public_live.json. Show the stated facts in a rehearsal take before recording; if a changed run produces different facts, update the script to match rather than altering the displayed results.

App: https://rehearsal-act3.aa0brkr65f1ep.us-east-1.cs.amazonlightsail.com/
Architecture: https://github.com/AbhishekSharma55/amd-act-3/blob/main/docs/ARCHITECTURE.md
Evaluation table: https://github.com/AbhishekSharma55/amd-act-3#provisional-extraction-evaluation

## Scene 1: The problem

**Screen:** Open the live application, show its URL briefly, then focus on the committed schedule. Keep Live API selected.

**Read:**

> So, imagine it’s ten in the morning, and one of your machines suddenly stops. You’ve still got an important order that needs to go out at four. Now you’ve got to work out what to move, what’ll be late, and what you can actually promise. That’s where Rehearsal comes in.

## Scene 2: The starting schedule

**Screen:** Point to the three machine rows and delivery markers. Keep the committed schedule visible.

**Read:**

> Let me show you. This is our demo shop: seven orders and three machines. These are made-up orders, with deadlines and jobs that are already running.

## Scene 3: Interpret the message on AMD

**Screen:** Click Demo, show the message, then click Read message. Record the real response; shorten only the waiting footage and label that edit 'Processing wait shortened'.

**Read:**

> I’ll use this message: Mill M two is down until two p.m. J seven still needs to ship at four, and overtime needs approval. Now, when I click Read message, DeepSeek V four Flash on AMD Token Factory turns that into suggested planning changes.

## Scene 4: Source-linked review

**Screen:** Scroll to Constraints. Hover or click a proposal to highlight its original words. Point to the interrupted-operation note and the overtime approval note. Do not reject a valid demo constraint.

**Read:**

> You can click any of these suggestions and see the words it came from. We check the machines, times, and conflicts against the shop’s data. And this overtime suggestion still needs a person’s approval before it can actually be used.

## Scene 5: The recovery decision

**Screen:** Click Find recovery plans. Show the keep-machines infeasible card, the Re-route to qualified machines card, the checker badge, and J2’s 190-minute lateness.

**Read:**

> Okay, let’s find a recovery plan. If we keep everything on its original machines, we can’t meet J seven’s deadline. Moving work to another qualified machine keeps J seven on time, but J two ends up one hundred and ninety minutes late. You can see that tradeoff right here. And this recovery plan has passed a separate schedule check.

## Scene 6: Rehearse the plan

**Screen:** Keep the Re-route plan selected. Leave repair overrun at 90 minutes and click Rehearse plan. Show the per-order outcome bars.

**Read:**

> Now, getting a plan is one thing. We also want to see what happens if a repair takes longer, or a job runs a bit slow. So I’ll click Rehearse plan. That runs five hundred simulated scenarios, keeping the machine order fixed.

## Scene 7: Show the failure

**Screen:** Point to J4: 239 of 500. Click Show a failure; show the failing timeline and highlighted M1 bottleneck. Do not change replay assumptions.

**Read:**

> Okay, look at J four. It’s on time in the plan, but it only makes it in two hundred and thirty-nine of these five hundred scenarios. Click Show a failure, and we can see where it gets delayed. Those numbers come from our simulation assumptions, not real factory measurements.

## Scene 8: Approve and export

**Screen:** Click the Recovery plan tab to reveal approval. Tick the required J2 late-delivery concession, type Abhishek Sharma, and click Approve and export. Show both downloads and briefly open the CSV.

**Read:**

> For this demo, I’ll accept J two’s late delivery, add my name, and approve the plan. The server checks it again before giving us the downloads. There’s a dispatch CSV, plus a record of the changes, approvals, AMD response, and simulation results.

## Scene 9: A message that needs a person

**Screen:** In a second tab, open a fresh app session. Click Unknown machine, then Read message. Show the unknown machine/missing-time review notices and disabled Find recovery plans. Record as a separate take; leave the completed main run intact.

**Read:**

> Now, just to show you what happens with an unclear message: Mill four is down after lunch. We don’t have a Mill four, and we don’t have clear times. So it flags those fields and blocks planning until they’re sorted out.

## Scene 10: Prove the AMD contribution

**Screen:** Return to the main run tab. Open Run inspector and show live AMD call, AMD Token Factory, model, host, latency and Raw model output. Then switch to the architecture diagram for the CPU/AMD explanation.

**Read:**

> And here’s the actual AMD call in the run inspector. You can see the model, how long it took, and what it returned. AMD handles reading the message. The OR-Tools solver, separate schedule checker, and NumPy simulation run on CPU.

## Scene 11: Measured evidence

**Screen:** Show the README’s Provisional extraction evaluation table. Keep both label sets, the rule baseline and the development-results qualification visible.

**Read:**

> We also tried twenty-three messages we wrote ourselves. Our basic rules got thirteen right. The AMD model got twenty-three using Muskan’s labels, and twenty-one using mine. We used these messages to improve the prompts, so these are early development results, with the labels still being finalized.

## Scene 12: Value and close

**Screen:** Return to the recovery plan or app homepage. End with Rehearsal, Forge Ahead, and the two team names on screen.

**Read:**

> The aim is to help a planner see the options, understand the risks, and keep a clear record of the decision. Next, we want to try this with real planners and measure whether it helps. I’m Abhishek, and I built this with Muskan. We’re Forge Ahead, and this is Rehearsal.
