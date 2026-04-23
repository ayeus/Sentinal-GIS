# 1 INTRODUCTION

## 1.1 Introduction to Project
In an era where data moves faster than ever, public health tracking often still lags behind. SentinelGIS was built to bridge that gap. At its core, the project is an intelligent mapping and prediction platform meant to spot disease outbreaks before they spiral out of control. Instead of just relying on past records, the system pulls together historical trends and live news feeds, feeding all of that into a machine learning engine. The end result is a dynamic map that gives health workers a realistic look at where something like Dengue or Malaria might hit next.

## 1.2 Problem Statement and Description
If you look at how local authorities handle outbreaks right now, the process is incredibly reactive. They often rely on manual reports—like the weekly PDFs published by government health portals. The problem is obvious: by the time the PDF is typed up, reviewed, and published, a localized outbreak could have easily jumped across district lines. Furthermore, crucial early clues hidden in local news reports or sudden spikes in hospital chatter go completely ignored because there’s no centralized system designed to catch them. We simply lack a spatial forecasting tool that tells us where the fire will spread, rather than just pointing out where it already burned.

## 1.3 Motivation
The real driving force behind SentinelGIS was the desire to flip the script on disease management. We wanted to move from a "wait and respond" approach to something genuinely proactive. By setting up automated scrapers that read the news and algorithms that analyze past patterns, we can give medical professionals the heads-up they need. If you know a neighboring district has a high risk of an outbreak next month, you can start moving supplies and personnel there today.

## 1.4 Sustainable Development Goal of the Project
This entire initiative is tightly aligned with the United Nation's Sustainable Development Goal 3, which emphasizes "Good Health and Well-being." A major target within SDG 3 is upgrading early warning systems and risk reduction strategies, which is exactly what this software aims to accomplish on a regional level.

---

# 2 LITERATURE SURVEY

## 2.1 Overview of the Research Area
When digging into the current state of epidemiological technology, it becomes clear that the field is shifting. Researchers are increasingly trying to mix classic geographic information systems (GIS) with modern artificial intelligence. A lot of the newer studies focus on using natural language processing to mine Twitter or local news for early signs of sickness, combining those informal signals with hard clinical data.

## 2.2 Existing Models and Frameworks
Historically, epidemiologists have leaned heavily on mathematical models like SIR or SEIR to guess how a virus might spread. These are foundational, but they require very strict biological assumptions that are hard to get right in real time. On the other hand, national surveillance networks (like the IDSP in India) do the heavy lifting of gathering real data, but they distribute it in flat, static documents. While there are a few global threat dashboards like HealthMap, they rarely offer the hyper-local, district-by-district forecasting needed by workers on the ground.

## 2.3 Limitations Identified from Literature Survey (Research Gaps)
The biggest blind spot we noticed is the disconnect between different types of data. You have machine learning models operating in isolation on five-year-old datasets, and you have live news alerts that nobody is quantifying. Furthermore, turning these complex risk calculations into a map that is actually intuitive and fast enough for a browser has remained a surprisingly tough technical hurdle.

## 2.4 Research Objectives
- Create a script that autonomously grabs and reads government health PDFs.
- Program an NLP tool to constantly monitor RSS feeds for specific disease keywords and locations.
- Train a spatial-temporal model (like a Random Forest) to figure out the mathematical risk for individual districts based on what happened in the previous months.
- Tie it all together in a fast, interactive React dashboard that anyone can understand without a data science degree.

## 2.5 Product Backlog (Key user stories with Desired outcomes)
- **The Ground Worker:** "I need a color-coded map so I can see instantly which towns are in the red zone this month." *(Outcome: The AI Forecast Map)*
- **The Analyst:** "I want to see if the AI predictions match up with what the local newspapers are saying right now." *(Outcome: Live Intelligence Center)*
- **The Researcher:** "I need to look at historical charts to see if these diseases usually happen at the same time." *(Outcome: Advanced Analytics)*
- **The Developer:** "The database needs to fetch new info by itself, so I don't have to manually upload CSVs every weekend." *(Outcome: Automated Scraper Pipeline)*

## 2.6 Plan of Action (Project Road Map)
The build was broken down into logical phases. First, we had to get the data—scraping the old PDFs and cleaning up the mess. Once the data was formatted, we moved on to the machine learning phase, figuring out how to teach an algorithm to recognize temporal patterns. The third step was writing the actual backend APIs in FastAPI to serve those predictions. Finally, we brought it to life visually using React and Leaflet for the frontend interface.

---

# 3 SPRINT PLANNING AND EXECUTION METHODOLOGY

## 3.1 SPRINT I: The Data Foundation and Predictive Engine

### 3.1.1 Objectives with user stories of Sprint I
For the first sprint, the goal was purely backend. We needed to prove that the machine learning concept actually worked. 
- *Story:* As the lead modeler, I need a reliable, clean dataset of past outbreaks so I can train the Random Forest.

### 3.1.2 Functional Document
We built a series of Python scripts. One script was responsible for navigating the web and pulling down PDFs. Another used feature engineering to create "lag" variables—basically, looking at the number of cases a district had 30 or 60 days ago to predict what will happen next. 

### 3.1.3 Architecture Document
The flow was relatively straightforward: Raw PDFs went in, a cleaning engine parsed the tables, and a processed CSV came out. We then fed that CSV into a Scikit-Learn Random Forest setup, which eventually exported the trained model as a serialized pickle file.

### 3.1.4 Outcome of objectives/ Result Analysis
The model performed surprisingly well. We managed to create a dataset that properly mapped the relationship between a specific state, its districts, and various diseases over time. The algorithm got really good at flagging "High Risk" scenarios, which was our main priority since missing a major outbreak is far worse than occasionally over-predicting a minor one.

### 3.1.5 Sprint Retrospective
Looking back, teaching the algorithm to handle the time-series data was easier than expected. The real nightmare was the PDF scraping. Government documents are notoriously inconsistent, so we spent way too much time writing regex rules just to get clean numbers. It taught us to expect messy data moving forward.

---

## 3.2 SPRINT II: Live Data and Visual Interface

### 3.2.1 Objectives with user stories of Sprint II
Now that the brain worked, we needed a face for the software, plus the live-news tracking element.
- *Story:* As an official looking at the screen, I want an interactive map that I can click around to see live threats.

### 3.2.2 Functional Document
We fired up a FastAPI server to act as the middleman. It handled the heavy lifting of running the ML model and also parsed live RSS feeds from the WHO and Google News. On the frontend, we used React to build a dynamic dashboard that could render thousands of GeoJSON district polygons without crashing the browser.

### 3.2.3 Architecture Document
The architecture relied on Uvicorn running our Python endpoints. When a user changes the year or disease dropdown on the React site, it triggers a fetch request. The backend does the math, returns JSON, and React-Leaflet instantly repaints the map colors.

### 3.2.4 Outcome of objectives/ Result Analysis
We successfully managed to get the news alerts mapped to physical coordinates. If an article mentioned "Dengue in Kerala," the system caught it, categorized the severity, and pinged the dashboard. The transitions between looking at old data and checking the new AI forecasts felt seamless and snappy.

### 3.2.5 Sprint Retrospective
The split between the FastAPI backend and the React frontend was a lifesaver. It let us tweak the UI without risking the integrity of the predictive models. However, rendering the high-detail map of India initially caused some lag, which forced us to optimize the GeoJSON files.

---

# 6 RESULTS AND DISCUSSIONS

## 6.1 Project Outcomes (Performance Evaluation, Comparisons, Testing Results)
When we finally ran the full system tests, the results were highly encouraging. From an accuracy standpoint, the spatial-temporal model consistently beat out standard moving-average baseline models. It proved that taking neighboring districts and historical lags into account genuinely improves prediction quality. 

On the performance side, the FastAPI backend was consistently serving map data and complex ML predictions in under 150 milliseconds. This meant the React frontend felt instantly responsive. Additionally, the real-time news scraper accurately filtered out the noise, mapping the vast majority of disease-related news snippets to their correct geographic locations. The visual layout—using a clear red-to-green heat scale—proved immediately intuitive during our testing, validating the core concept of the project.

---

# 7 CONCLUSION AND FUTURE ENHANCEMENT

Looking back at the development cycle, SentinelGIS proves that we can absolutely move past outdated, manual surveillance methods. By hooking up automated web scrapers with advanced predictive algorithms, and packaging the whole thing in a clean web app, we created something that bridges the gap between raw data and actual human decision-making. 

As for what comes next, there is a lot of room to grow. We want to push the map granularity even further, going down from districts to the local sub-district or Tehsil level. It would also be highly beneficial to swap out our basic keyword-search logic with a more advanced Large Language Model (LLM) to better understand the context of news articles. Finally, incorporating live weather APIs—since rain directly impacts diseases like Malaria—would add an entirely new layer of accuracy to the forecasts.

---

# REFERENCES
1. Scikit-learn Developers. (2023). Scikit-learn: Machine Learning in Python.
2. FastAPI Documentation. (2023). FastAPI framework, high performance, easy to learn, fast to code, ready for production.
3. React Documentation. (2023). React – A JavaScript library for building user interfaces.
4. IDSP (Integrated Disease Surveillance Programme), Ministry of Health and Family Welfare, Government of India. Weekly Outbreak Reports.
5. Brownstein, J. S., Freifeld, C. C., & Madoff, L. C. (2009). Digital disease detection—harnessing the Web for public health surveillance. New England Journal of Medicine.
