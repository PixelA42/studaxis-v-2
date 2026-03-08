# Problem Statement — Studaxis

**AWS Hackathon 2026 | Student Track 1**

---

## 1. The Access Gap

Students in Tier-2 and Tier-3 regions of India frequently receive government-issued laptops (4GB–8GB RAM, Intel i3/i5 processors) but lack consistent internet connectivity. Existing EdTech solutions—including ChatGPT, Khanmigo, and similar platforms—require persistent streaming connections, rendering them **unusable in offline environments**.

### Impact

When connectivity fails, learning productivity drops to zero. Students lose access to:

- AI-powered feedback on written answers
- Automated grading of subjective responses
- Contextual explanations grounded in curriculum
- Adaptive difficulty and personalized tutoring

This happens precisely when students need support most—at home, during self-study hours, in rural and semi-urban areas where connectivity is unreliable.

---

## 2. Scale of the Problem

| Metric | Value |
|--------|-------|
| **Target population** | 264 million students in India (Tier-2/3) |
| **Device availability** | Government-issued laptops (4GB RAM, i3 CPUs) |
| **Connectivity reality** | 60%+ lack reliable broadband |
| **Current AI tools** | ChatGPT, Khanmigo, Google Gemini — **unusable at 0 kbps** |

---

## 3. Competitive Landscape

| Solution | Offline Capability | Min Hardware | Cost | Limitation |
|----------|-------------------|--------------|------|------------|
| **ChatGPT / GPT-4** | ❌ None | N/A (cloud) | $20/month | 100% cloud-dependent; unusable at 0 kbps |
| **Khanmigo (Khan Academy)** | ❌ None | N/A (cloud) | $44/year | Streaming required; no offline mode |
| **Google Gemini** | ❌ None | N/A (cloud) | Free | Cloud-only; no edge deployment |
| **Duolingo** | ⚠️ Partial | 2GB RAM | Free/Premium | Limited offline; lessons only, no AI tutoring |
| **BYJU'S** | ⚠️ Video cache | 4GB RAM | ₹10K+/year | Video downloads only; no AI grading offline |
| **Studaxis (Ours)** | ✅ **100%** | **4GB RAM** | **Free** | Full AI tutoring, grading, RAG at 0 kbps |

**Differentiation:** Studaxis is the only solution offering **complete AI tutoring functionality offline** on entry-level hardware.

---

## 4. Why This Matters for Education

- **Pupil–Teacher Ratios:** Rural schools often reach 40:1+; AI enables 1-on-1 tutoring at scale.
- **Economic Mobility:** Better AI-assisted preparation improves exam scores and placement rates for 1.5M+ annual engineering graduates.
- **Language Inclusion:** Hinglish support reduces English proficiency barriers for 57% of students in Hindi-medium schools.
- **Device Activation:** Activates millions of underutilized government-issued laptops for self-study.

---

## 5. Problem Statement (Clear Context for Evaluators)

**In one sentence:**  
*264 million Indian students have government-issued laptops but lack reliable internet—existing AI tools (ChatGPT, Khanmigo) are unusable at 0 kbps, so when connectivity fails, learning productivity drops to zero.*

**Studaxis addresses this by delivering 100% of core AI tutoring features—chat, grading, quizzes, flashcards, RAG—entirely offline on 4GB RAM devices, at 0 kbps bandwidth.**
