# Theory Wellness — Application Question Answers

Drafted 2026-04-18. Source: Indeed application for Director of Data Intelligence & Automation.

---

## Q1. Are you at least 21 years of age? (Must be 21 to apply)

Yes.

---

## Q2. Describe a data or reporting system you personally designed and built that changed how a business made decisions. What was the problem, what did you build, and what was the measurable impact?

At Nightjar (Sept 2023–Jan 2025), I inherited a retail operation running on Dutchie with no real link between promotions, vendor credits, and the back-office merchandising calendar. Promo decisions lived in email threads, got reported on via manual pulls, and hit vendor-credit reconciliation weeks later. Margin-at-risk was invisible until finance caught it.

I built an API-driven Dutchie Backoffice integration into Google Sheets that pulled transaction data, inventory movement, and promo metadata on a schedule, then tied that data into a unified promo-planning workflow with explicit launch, takedown, and reconciliation stages and standardized vendor-credit tracking categories. SKU rationalization and open-to-buy methodology ran off the same data spine.

The store scaled from $200K to $400K monthly gross revenue during my tenure, and we recovered $70K in vendor credit splits in FY 2024 that the prior reconciliation process had been missing. More durably, promo decisions became post-mortem-able. "Did this promo actually move the SKUs we needed to move, at the margin we wanted" became a question the team could answer in hours instead of weeks.

---

## Q3. Have you led or been directly involved in implementing AI tools (LLMs, automation, machine learning) in a business setting? If so, describe what you deployed, how you drove adoption, and what you learned.

Yes. LLM-based automation is the center of my 2025 Fractional practice.

I built a multi-agent Notion CRM for Freed Solutions' own operations and for client work. Six databases (Contacts, Companies, Action Items, Meetings, Emails, Domains) wired together, with four specialized LLM-powered agents running distinct workflows. A Post-Meeting agent turns calendar transcripts into CRM wiring, curated summaries, and action items. A Post-Email agent summarizes threads and matches them to existing work. A nightly enrichment agent closes QC gaps on draft contacts and companies. A Follow-Up agent cross-matches new activity to open action items. On top of that CRM sits a Claude Code skill library (Notion Action Items, Meeting Prep, Agent Config, Pandoc Deliverables, Review Analysis, Inventory Reconciliation) with a shared gate taxonomy that tells the automation when to proceed, when to ask, and when to stop. MCP integrations across Notion, Google Workspace, Monday, Figma, and Calendly turn the LLM into an operating layer over existing business systems instead of another siloed tool.

Adoption started internal. My own consultancy runs on this daily, which gave me real user feedback before scaling to client work. The system is now the spine of my Theory Wellness engagement (18 stakeholder interviews wired live, with meeting notes, follow-up emails, and action items cross-linked) and a parallel Fractional client.

A few lessons worth calling out. Foundation-before-tools isn't optional. I learned the hard way that AI layered onto a dirty data foundation amplifies noise faster than it reduces it, which shapes how I now recommend every MSO sequence its AI rollout. Governance discipline pays for itself: an explicit gate taxonomy lets agents run autonomously on routine work and still catch risky changes before they land. And AI adoption sticks when it eliminates work, not when it automates around work. The goal is fewer sheets and fewer processes, not AI-driven versions of the same bloat.

---

## Q4. This role supports every department in a vertically integrated, multi-state cannabis company, from cultivation and manufacturing to retail, finance, and compliance. Describe your experience working cross-functionally across multiple business areas with competing data needs. How did you prioritize?

Cross-functional is my entire career trajectory. I started on the floor at NETA as an Inventory Coordinator in 2015 and moved through Production, Operations, and Compliance management before landing as Director of Systems. I've lived the operational reality of every department this role supports. At Parallel I held a dual role (MA Market IT plus Enterprise Supply Chain IT across five markets), translating the gap between a single market's needs and shared-services priorities. At Insa I built the Systems department across FL/MA/OH/CT/PA, supporting Retail, Marketing, Operations (Cultivation/Manufacturing/Distribution), Planning & Allocations, Supply Chain & Procurement, Finance & Costing, and HR while co-supporting a Sage X3 ERP deployment. Most recently at Theory Wellness, I've completed 18 discovery interviews across every function the JD lists.

On prioritization, my working rule is that foundation requests beat feature requests. When Compliance wants a new report and Production wants a data integrity fix on the same dataset, the integrity fix goes first. Reports built on bad data degrade trust and create rework; I watched a Supply Chain 2.0 sheet error at a prior client go undetected for a full year, and the downstream reallocation cost dwarfed any short-term reporting delay.

Beyond that, I use cross-stakeholder validation as a signal. When one department is loud about a problem, I check whether adjacent departments see the same problem. At Theory, the "missing centralized IT" theme had four independent surfacings before Eddie validated it himself; that's different signal weight than a one-off request.

And I push to resolve the "how" questions (process, ownership, flow) before jumping to "what" (tool selection), because picking a tool without answers to the process questions just buys the wrong solution faster.

---

## Q5. What's your experience with SQL, Python, and cloud data platforms? Give a specific example of a technical project where you were hands-on, not just managing.

To be direct: I'm a low-code developer and AI-paired builder, not a traditional software engineer. Hands-on for me means I write the code, I own the outcomes, and I lean on modern AI tooling (specifically Claude Code) to accelerate production-grade work. The code gets written. I also bring deep domain knowledge of what the code needs to do, which matters more than it sounds.

On SQL, I'm read-fluent across SQL Server and Snowflake in cannabis MSO warehouses (Dutchie, METRC, Apex feeds). I'm comfortable with joins, window functions, and stored-procedure logic in reporting contexts. For production DDL and performance tuning I lean on DBAs and data engineers.

On Python, my use is scripting and automation via Claude Code rather than production Python engineering. I own the business logic, the scope, and the validation; AI-paired development produces the implementation. At Theory I've worked shoulder-to-shoulder with their in-house Python developer (Shaun Seward) on his Metrc-automation pipeline, so I know where low-code plus AI-paired work complements traditional engineering.

On cloud data platforms, I've worked inside Snowflake at multiple cannabis operators, and I'm familiar with MCP-based architectures sitting over Snowflake (which is Theory's current direction). Earlier roles put me inside AWS and GCP environments via MSO stacks, though I've never been the cloud architect of record.

For a specific hands-on project: my 2025 multi-agent Notion CRM. I personally designed the schema (six databases with relation/rollup topology, QC formulas for required-fields dedup), implemented the four AI agents with explicit gate protocols for autonomous vs. paused operation, built MCP integrations across Notion, Google Workspace, Monday, Figma, and Calendly, and shipped a Claude Code skill library with closeout and regression-test scripts plus sync tooling across Codex and Claude runtimes. The whole thing is version-controlled, has a documented Rules of Engagement contract, and is the operating spine my Fractional practice runs on every day.

What that shows: I can take a messy operational problem, define the data model, implement the automation, govern the rollout, and run the resulting system in production. All while being honest that I'm doing it with AI-paired development, not traditional SWE work. For a role explicitly about AI deployment and automation strategy in a domain I know cold, that's the thing.

---

## Q6. What are your compensation expectations for this role?

$150,000 to $160,000 base, with openness to discussing structure around the ESOP, equity, and broader package. Happy to have a separate conversation on Fractional rate structure if that's useful.

---

*Notes for Adam (remove before submission):*
- $150K–$160K range anchored to (a) the $150K floor you already gave Eddie, and (b) your inflation-adjusted Insa rate of ~$156.67K. Asking at $160K creates room to land at the $150K floor on the other side of a negotiation.
- Q5 leads with the low-code framing on purpose. Owning it in writing is better than getting called out in a live interview.
- Q3 weaves in the Theory engagement without flagging it as a conflict; reads as "I built this and it's already the spine of my practice."
- Q4 cites the Supply Chain 2.0 incident anonymously ("a prior client") to avoid breaking discovery confidentiality.
