# 1 INTRODUCTION

## 1.1 Introduction to Project
SentinelGIS is a mapping and forecasting platform for disease outbreaks in India. It reads the weekly outbreak reports published by the Integrated Disease Surveillance Programme (IDSP), turns them into a clean, district-level record, and estimates where outbreaks are most likely to be reported in the coming four weeks. Alongside that record it shows official WHO outbreak notices and recent news headlines. The aim is to give health workers one place to see what has been reported, what may come next, and how far each of those views can be trusted.

## 1.2 Problem Statement and Description
Outbreak information in India is published as weekly PDF bulletins. Each bulletin is a set of tables: one row per outbreak, with state, district, disease, cases, deaths and dates. The information is valuable but hard to use. It cannot be mapped, compared across weeks or searched without retyping it, and nothing in it looks forward. Early clues in news reports sit in a separate world altogether. There is no tool that joins these into a district-level picture and a forecast.

## 1.3 Motivation
We wanted to move from reading last week's PDF to asking "where should we look first next month?". If a district has a raised chance of a measles or hepatitis outbreak, supplies, vaccination drives and staff can be planned ahead. Because such a tool may influence real decisions, a second motivation grew during the project: everything shown must be traceable to its source, and the forecast must come with an honest account of how often it is right.

## 1.4 Sustainable Development Goal of the Project
The project supports United Nations Sustainable Development Goal 3, "Good Health and Well-being", in particular the target of strengthening early warning and risk reduction for health risks.

---

# 2 LITERATURE SURVEY

## 2.1 Overview of the Research Area
Digital epidemiology combines geographic information systems with statistical and machine-learning models. Two strands are relevant here: forecasting from official surveillance records, and event-based surveillance, which mines news and other informal sources for early signals.

## 2.2 Existing Models and Frameworks
Compartmental models such as SIR and SEIR describe how an infection moves through a population, but they need biological parameters that are rarely known for a local outbreak in real time. National surveillance programmes such as IDSP collect real outbreak reports but publish them as static documents. Global dashboards such as HealthMap aggregate informal signals but do not offer district-level forecasting for India.

## 2.3 Limitations Identified from Literature Survey (Research Gaps)
Official records and informal signals are rarely brought together. Forecasting studies often report a single accuracy figure on randomly split data, which overstates performance for rare events and lets information from the future leak into training. And turning district-level results into a map that loads quickly in a browser remains a practical hurdle.

## 2.4 Research Objectives
- Automatically collect and read IDSP weekly outbreak bulletins.
- Build a clean, district-level outbreak record with every figure traceable to a bulletin.
- Forecast the probability of a reported outbreak per district and disease, and test it strictly forward in time.
- Monitor official outbreak notices and news feeds for mentions of Indian states.
- Present all of this in an interactive dashboard that states its own limitations.

## 2.5 Product Backlog (Key user stories with Desired outcomes)
- **The Ground Worker:** "I need a colour-coded map so I can see which districts reported outbreaks, and which are most at risk next." *(Outcome: Surveillance and Forecast maps)*
- **The Analyst:** "I want to know how often a High-risk flag turns out to be right." *(Outcome: Data & Model page with test results)*
- **The Researcher:** "I need trends over time and to see which diseases are reported together." *(Outcome: Analytics)*
- **The Developer:** "The system should fetch new bulletins by itself." *(Outcome: Automated pipeline)*

## 2.6 Plan of Action (Project Road Map)
The work proceeded in phases: collect and parse the bulletins; clean the data and place it on a district map; build and test the forecasting model; expose everything through FastAPI; and build the React interface.

---

# 3 SPRINT PLANNING AND EXECUTION METHODOLOGY

## 3.1 SPRINT I: The Data Foundation and Predictive Engine

### 3.1.1 Objectives with user stories of Sprint I
- *Story:* As the modeller, I need a reliable dataset of past outbreaks before any model can be trusted.

### 3.1.2 Functional Document
A scraper reads the official index of weekly reports (now on the NCDC website) and downloads one bulletin per reporting week. The older IDSP page, whose links partly pointed to Google Drive, is still understood, and when the official server cannot be reached the Internet Archive's copies of the same files are used. An extractor reads every outbreak row from the PDF tables, and a cleaning step resolves district names to a 2021 boundary layer, standardises disease names, validates dates against the reporting week and merges follow-up rows. A data-quality report records what could not be resolved.

### 3.1.3 Architecture Document
PDF bulletins → extracted rows (`historical_cases_raw.csv`) → clean outbreak record (`historical_cases_clean.csv`) and coverage report (`data_quality.json`) → weekly district-by-disease panel → gradient-boosted classifier → forecast table and model card.

### 3.1.4 Outcome of objectives/ Result Analysis
The record holds **13,828 outbreaks** (about 521,000 cases and 3,259 deaths) from **446 of the 450 weekly bulletins** between January 2018 and 16 August 2026. 99.7% of outbreaks are placed on a district; the rest are mostly outbreaks reported for several districts at once.

The first model built in this sprint did not work, and it is worth recording why. It was a Random Forest predicting next month's case band, evaluated on a random split, and it reported 88% accuracy. That figure came almost entirely from predicting "no outbreak": it identified none of the High-risk cases and about 5% of the Low and Medium ones. The application also displayed its output for rows it had been trained on. It was replaced.

The current model answers a narrower, learnable question: will IDSP report at least one outbreak of this disease in this district within four weeks? It uses the district's own history, neighbouring districts, the rest of the state and the season, and treats weeks without a bulletin as unknown rather than quiet. It was tuned on older weeks and then scored once on the most recent 16 labelled weeks (April to July 2026), which took no part in tuning or fitting:

| Risk tier | Share of forecasts | Outbreak actually followed | Share of all outbreaks |
| --- | --- | --- | --- |
| High (20% or more) | 0.6% | 32% | 17% |
| Medium (8% or more) | 2.5% | 9% | 22% |
| Low (3% or more) | 6.3% | 4.8% | 28% |
| Minimal | 90.7% | 0.4% | 34% |

Average precision was 0.182, against 0.131 for the best simple rule (how often the disease was reported in the district over the past year) and 0.011 for random guessing; ROC-AUC was 0.89. These figures are regenerated each time the model is retrained on new bulletins, and an earlier test period (October 2025 to January 2026) gave similar results (0.192 against 0.128).

### 3.1.5 Sprint Retrospective
The hardest part was the data, not the model. The PDF tables shade individual lines of text, which the parser mistook for cell borders; for a long time every bulletin from 2025 onward failed silently and the application ran on data that stopped in 2023. Many weeks were missing because the official index links them through Google Drive, which the first scraper skipped. The lesson was to measure coverage explicitly and to treat a good-looking accuracy figure with suspicion until it has been tested on data from the future.

---

## 3.2 SPRINT II: Live Data and Visual Interface

### 3.2.1 Objectives with user stories of Sprint II
- *Story:* As an official, I want an interactive map of reported outbreaks and forecasts, and to see current notices and news for my state.

### 3.2.2 Functional Document
A FastAPI server serves the outbreak record, the forecast, analytics, and live signals from WHO Disease Outbreak News and news RSS feeds. The React frontend draws 735 districts with Leaflet and offers five pages: Surveillance, Forecast, Analytics, Live Signals, and Data & Model.

### 3.2.3 Architecture Document
Uvicorn runs the Python endpoints. A background scheduler checks for new bulletins daily, and each new bulletin triggers re-extraction, cleaning, retraining and a new forecast. The frontend reads JSON from the API; the district and state boundaries are static files.

### 3.2.4 Outcome of objectives/ Result Analysis
All pages work against the real record. Every page carries a banner stating how old the newest bulletin is. Live items are matched to states by the names mentioned in their text; news items are labelled as unverified media reports and WHO notices as official. Disease guidance is a summary of WHO and CDC fact sheets, each linked to its source.

We have not measured the accuracy of the news-to-state matching against a hand-labelled sample, nor benchmarked API response times; both remain to be done.

### 3.2.5 Sprint Retrospective
Separating the API from the interface made it possible to rebuild the data and model without touching the pages. Replacing the district boundary file (34 MB, early-2000s boundaries) with a simplified 2021 layer (6 MB) removed both the loading lag and the mismatch that had kept about a quarter of outbreaks off the map.

---

# 6 RESULTS AND DISCUSSIONS

## 6.1 Project Outcomes (Performance Evaluation, Comparisons, Testing Results)
**Data.** 13,828 outbreaks from 446 of 450 weekly bulletins (January 2018 to 16 August 2026). Four weeks are missing because the official index links them to another week's document.

**Forecast.** On unseen weeks the model ranks about 1.4 times better than the best simple rule. A High flag was followed by a reported outbreak 32% of the time, about thirty times the average rate. The limits are equally clear. Most flags, including most High flags, are not followed by an outbreak, and 34% of outbreaks occurred where risk was rated Minimal. Performance varies by disease and by season: in the April to July 2026 test it was useful for dengue, hepatitis, typhoid and chickenpox (average precision 0.24 to 0.51) and close to useless for cholera, leptospirosis and rabies, while in the earlier winter test dengue was weak and mumps and malaria were strong. Neighbouring-district outbreaks contributed almost nothing to accuracy; the district's own history and activity elsewhere in the state mattered most.

**What the forecast means.** The model predicts *reporting*. States that report thoroughly appear at higher risk, and an outbreak that was never reported is invisible. The tool can help decide where to look first; it cannot rule a district out.

**Software.** 20 backend unit tests cover scraping, PDF parsing, cleaning, district-name resolution and the guarantee that forecast features never use future data; the frontend builds without warnings.

---

# 7 CONCLUSION AND FUTURE ENHANCEMENT

SentinelGIS shows that the weekly IDSP bulletins can be turned automatically into a reliable district-level record, and that this record supports a modest but real forecast. The honest summary is that the surveillance side is solid and the forecasting side is a useful ranking aid with known error rates, not an oracle.

Future work, in order of expected value:
- **Keep the data current.** The original IDSP website was retired during the project and the reports moved to the NCDC website; the scraper now follows that page and checks it every six hours. Official publication runs several weeks behind (at the time of writing, 12 October 2026, the newest bulletin covers the week ending 16 August 2026), so the system is as current as the source allows, not real-time.
- **Add external drivers.** Rainfall, temperature and population data are likely to help with vector-borne and water-borne diseases, where the model is weakest.
- **Validate the live signals.** Measure the news-to-state matching against a hand-labelled sample, or replace keyword matching with a language model and measure that.
- **Clinical review.** Have the disease guidance text reviewed by a public-health professional.
- **Finer geography.** Move below district level where the bulletins give block or village names.

---

# REFERENCES
1. Integrated Disease Surveillance Programme (IDSP), National Centre for Disease Control, Ministry of Health and Family Welfare, Government of India. Weekly Outbreak Reports. https://ncdc.mohfw.gov.in/includes/WeeklyOutbreaks.php
2. Pedregosa, F. et al. (2011). Scikit-learn: Machine Learning in Python. Journal of Machine Learning Research, 12, 2825-2830.
3. Runfola, D. et al. (2020). geoBoundaries: A global database of political administrative boundaries. PLoS ONE, 15(4).
4. World Health Organization. Disease Outbreak News. https://www.who.int/emergencies/disease-outbreak-news
5. Brownstein, J. S., Freifeld, C. C., & Madoff, L. C. (2009). Digital disease detection: harnessing the Web for public health surveillance. New England Journal of Medicine, 360(21), 2153-2157.
6. FastAPI documentation, https://fastapi.tiangolo.com; React documentation, https://react.dev.
