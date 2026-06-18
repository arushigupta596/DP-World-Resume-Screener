"""Generate 30 synthetic CVs (PDFs) for demo testing of the DP World CV screener.

Spread:
- 8 strong matches (expect Shortlist >=70): offshore/maritime + market analysis + tooling
- 9 mid matches (expect Review 50-69): partial fit
- 8 weak matches (expect Reject <50): wrong field or no fit
- 5 edge cases: bonus tools, risk flags, short tenures, no MS tools, academic-only

All names/companies are fictitious. Output: /Users/arushi/Desktop/DP_World/sample-cvs/
"""
from __future__ import annotations

import pathlib
import re

from fpdf import FPDF

OUT_DIR = pathlib.Path("/Users/arushi/Desktop/DP_World/sample-cvs")
OUT_DIR.mkdir(parents=True, exist_ok=True)


_UNICODE_REPLACEMENTS = {
    "—": "-",  # em dash
    "–": "-",  # en dash
    "‘": "'",
    "’": "'",
    "“": '"',
    "”": '"',
    "…": "...",
    " ": " ",  # non-breaking space
    "•": "*",
}


def _sanitize(s: str) -> str:
    for k, v in _UNICODE_REPLACEMENTS.items():
        s = s.replace(k, v)
    return s.encode("latin-1", errors="replace").decode("latin-1")


def render_pdf(name: str, body: str, file_name: str) -> None:
    pdf = FPDF(format="A4")
    pdf.set_margins(15, 15, 15)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    text_width = pdf.w - pdf.l_margin - pdf.r_margin

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(text_width, 9, _sanitize(name), ln=1)
    pdf.set_font("Helvetica", "", 10)

    for raw_line in body.strip().splitlines():
        line = _sanitize(raw_line.rstrip())
        if not line:
            pdf.ln(3)
            continue
        if line.endswith(":") and len(line) < 40:
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(text_width, 6, line, ln=1)
            pdf.set_font("Helvetica", "", 10)
            continue
        pdf.multi_cell(text_width, 5, line)

    pdf.output(str(OUT_DIR / file_name))


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


CVS: list[dict] = []


def add(name: str, headline: str, body: str) -> None:
    CVS.append({"name": name, "headline": headline, "body": body})


# === STRONG MATCHES (expect Shortlist >= 70) ===
add(
    "Sarah Mitchell",
    "Senior Market Analyst | Offshore OSV & Subsea",
    """
sarah.mitchell.demo@example.com  |  Aberdeen, UK  |  +44 7700 900111

Professional Summary:
Senior market research analyst with 9 years of experience in the offshore OSV and subsea
segments. Built and maintained day-rate forecasting models tracked monthly by the executive
committee. Published quarterly Offshore Vessel Outlook used by the VP Commercial team to
shape new-build investment decisions worth USD 220M.

Experience:

Senior Market Analyst — North Sea OSV Solutions (2021 to present)
- Owned the OSV market intelligence function, reporting directly to the VP Commercial.
- Built day-rate and utilisation forecasting models in Excel + Power BI, refreshed weekly.
- Published the quarterly Offshore Vessel Outlook, cited in two board investment decisions.
- Subscribed primary user of Clarkson Research and Rystad Energy data feeds.
- Authored a competitor intelligence framework that fed a USD 60M tender win in 2023.

Market Analyst — Subsea Forecast Partners (2017 to 2021)
- Conducted competitor analysis for subsea EPC tenders across UK and Norwegian sectors.
- Developed advanced Excel models with VBA for fleet-availability scenarios.
- Built Power BI dashboards for the senior leadership team.

Junior Analyst — Aberdeen Marine Brokers (2015 to 2017)
- Daily reports on offshore vessel chartering activity in the North Sea.

Key Tools:
Clarkson Research, Rystad Energy, IHS Markit, Power BI, Advanced Excel (VBA, pivot tables),
PowerPoint, S&P Global Platts

Education:
MSc Energy Economics, Heriot-Watt University (2015)
BSc Economics, University of Edinburgh (2013)
""",
)

add(
    "James Thornton",
    "Market Intelligence Lead | Offshore Oil & Gas",
    """
james.thornton.demo@example.com  |  Houston, TX  |  +1 713 555 0142

Profile:
12 years in offshore oil & gas market intelligence. Currently leading a 4-person market
research team supporting a top-3 offshore drilling contractor. Frequent presenter to the
CEO and CFO on rig demand outlooks and competitor positioning.

Experience:

Market Intelligence Lead — Gulfstream Offshore Drilling (2019 to present)
- Manage all market research output: rig demand models, day-rate forecasts, competitor
  fleet tracking. Reports go directly to the C-suite monthly.
- Built the company's master forecasting model in Excel; outputs feed quarterly board pack.
- Heavy user of IHS Markit, S&P Global, and Rystad Energy for rig and exploration data.
- Analysis contributed to USD 180M asset acquisition decision in 2022.

Senior Analyst — Offshore Energy Research Group (2014 to 2019)
- Published syndicated reports on offshore drilling market trends across GoM, North Sea,
  West Africa and Brazil. Direct stakeholder dialogue with VP Commercial counterparts.
- Built Power BI dashboards rolled out to 30+ commercial users.

Analyst — Energy Strategies Inc (2012 to 2014)
- Market sizing and competitor profiling for offshore EPC clients.

Tools & Skills:
IHS Markit, S&P Global, Rystad Energy, Clarkson Research, Advanced Excel, Power BI,
Tableau, PowerPoint, scenario modelling

Education:
MBA — Finance, Rice University (2012)
""",
)

add(
    "Priya Sharma",
    "Offshore Wind Market Analyst",
    """
priya.sharma.demo@example.com  |  London, UK  |  +44 7700 900222

Summary:
Market analyst with 7 years of focused experience in offshore wind and offshore renewables.
Built forecasting models cited by senior leadership in tender go/no-go decisions.

Experience:

Market Analyst — North Sea Wind Capital (2020 to present)
- Lead market analyst for offshore wind, supporting the VP Commercial directly.
- Built supply-demand forecasting models for OFW installation vessels.
- Quarterly reports drive bid pricing on USD 300M+ EPC tenders.
- Heavy user of Clarkson Research's renewables intelligence and Rystad Energy.

Renewables Researcher — GreenGrid Analytics (2017 to 2020)
- Market sizing for floating wind and fixed-bottom offshore wind across Europe.
- Built Power BI dashboards tracking pipeline projects globally.
- Quarterly briefings to senior client stakeholders (VP/Director level).

Junior Analyst — Maritime Consulting Group (2016 to 2017)
- Researched offshore renewables and supply chain dynamics.

Tools:
Clarkson Research, Rystad Energy, IHS Markit, Advanced Excel, Power BI, PowerPoint

Education:
MSc Renewable Energy Systems, Imperial College London (2016)
""",
)

add(
    "David Wilson",
    "Senior Commercial Analyst | Subsea",
    """
david.wilson.demo@example.com  |  Stavanger, Norway

Profile:
8-year subsea market specialist. Track record of analytical work tied directly to
commercial wins. Familiar voice to senior decision-makers in offshore EPC.

Experience:

Senior Commercial Analyst — Subsea Solutions ASA (2018 to present)
- Reports to VP Commercial. Market intelligence support for Norwegian, UK and Brazilian
  subsea opportunities.
- Built scenario-based pricing models that informed three winning bids totalling USD 410M.
- Daily user of Clarkson Research and competitor fleet tracking via Rystad Energy.
- Advanced Excel (Power Query, dynamic arrays), Power BI dashboards used company-wide.

Analyst — Nordic Offshore Insights (2016 to 2018)
- Subsea market reports published quarterly to industry subscribers.

Tools:
Clarkson Research, Rystad Energy, Advanced Excel, Power BI, PowerPoint, Bloomberg Terminal

Education:
MSc Petroleum Economics, NTNU (2016)
""",
)

add(
    "Aisha Patel",
    "Maritime Commercial Analyst",
    """
aisha.patel.demo@example.com  |  Dubai, UAE

Summary:
6 years of maritime market analysis with strong exposure to offshore oil & gas customers
in the Middle East. Trusted analyst for VP-level commercial decisions.

Experience:

Maritime Commercial Analyst — Gulf Marine Logistics (2020 to present)
- Reports to the VP Commercial — Middle East. Owns market sizing and competitor tracking
  for OSV, AHTS and PSV demand from Aramco, ADNOC and NOC counterparts.
- Built day-rate forecasting models that drive fleet deployment decisions.
- Power user of BIMCO data and Clarkson Research.

Market Analyst — Red Sea Shipping Intelligence (2018 to 2020)
- Reported on Persian Gulf maritime trade dynamics.
- Built Power BI dashboards on tanker and OSV movements.

Tools:
Clarkson Research, BIMCO, Advanced Excel, Power BI, PowerPoint, AIS data tools

Education:
BSc Maritime Business, University of Plymouth (2018)
""",
)

add(
    "Carlos Rivera",
    "Offshore Oil & Gas Market Analyst",
    """
carlos.rivera.demo@example.com  |  Rio de Janeiro, Brazil

Profile:
8 years analysing offshore oil & gas markets in Latin America. Strong forecasting
discipline, regular contributor to executive strategy decisions.

Experience:

Market Analyst — Petrolat Offshore Services (2018 to present)
- Market intelligence lead for offshore drilling and FPSO segments in Brazil & Mexico.
- Built bottom-up FPSO demand forecasting models in Excel + Power BI.
- Insights presented monthly to VP Commercial and Chief Strategy Officer.
- Heavy user of Rystad Energy ServiceCube and IHS Markit upstream data.

Energy Analyst — Atlantic Strategy Consulting (2016 to 2018)
- Competitor intelligence reports for offshore EPC clients.

Tools:
Rystad Energy, IHS Markit, S&P Global, Advanced Excel (VBA), Power BI, PowerPoint

Education:
MSc Energy Economics, Universidade Federal do Rio de Janeiro (2016)
""",
)

add(
    "Liam Brennan",
    "OSV Commercial Strategist",
    """
liam.brennan.demo@example.com  |  Singapore

Summary:
7-year OSV market specialist. Analytical work has driven measurable commercial outcomes.

Experience:

Commercial Strategist — Pacific OSV Holdings (2019 to present)
- Reports to VP Commercial. Combines market analysis with bid pricing strategy for OSV
  charters in SEA and Australia.
- Authored the regional Offshore Vessel Quarterly. Direct input into a USD 95M long-term
  charter win in 2022 and a USD 140M renewal in 2024.
- Daily user of Clarkson Research, IHS Markit, Rystad Energy.
- Power BI dashboards used by sales and operations teams.

Market Analyst — South Asian Maritime Intelligence (2017 to 2019)
- Published quarterly OSV market reports across SEA.

Tools:
Clarkson Research, IHS Markit, Rystad Energy, Advanced Excel, Power BI, PowerPoint

Education:
MSc Maritime Economics, Erasmus University Rotterdam (2017)
""",
)

add(
    "Beatrice Hall",
    "Offshore Marine Market Researcher",
    """
beatrice.hall.demo@example.com  |  Aberdeen, UK

Summary:
8 years researching offshore marine sectors. Strong narrative skill but limited
Microsoft Office tooling depth (see below).

Experience:

Senior Researcher — Offshore Marine Reports (2018 to present)
- Authored quarterly OSV, AHTS and PSV market reports.
- Maintained competitor activity database for the UK and Norway.
- Direct contributor to VP Commercial briefings.
- Used Clarkson Research, IHS Markit and Rystad Energy daily.

Junior Researcher — Maritime Research Bureau (2016 to 2018)
- Researched offshore activity in the North Sea.

Note on tools:
Predominantly works in Google Workspace and proprietary data tools. Limited PowerPoint
and Excel exposure. No BI tooling history.

Education:
MSc Marine Resource Management, University of Aberdeen (2016)
""",
)


# === MID MATCHES (expect Review 50-69) ===
add(
    "Anna Kovac",
    "Logistics Market Analyst",
    """
anna.kovac.demo@example.com  |  Hamburg, Germany

Profile:
Market analyst with 5 years across container shipping and ports logistics. No direct
offshore exposure but adjacent maritime sector experience.

Experience:

Market Analyst — Hamburg Container Logistics GmbH (2021 to present)
- Tracks container freight rates, port congestion and trade flows.
- Built Power BI dashboards for senior management.
- Occasional contributor to strategy memos.

Analyst — Northern Ports Intelligence (2019 to 2021)
- Market sizing for port handling and inland logistics.
- Excel-based forecasting; some PowerPoint deliverables.

Tools:
Power BI, Advanced Excel, PowerPoint

Education:
MSc Logistics, Kuhne Logistics University (2019)
""",
)

add(
    "Marcus Lee",
    "Renewable Energy Market Analyst",
    """
marcus.lee.demo@example.com  |  Sydney, Australia

Summary:
Energy market analyst with 4 years focused on onshore renewables. Some exposure to
offshore wind in the last 12 months.

Experience:

Market Analyst — Pacific Renewables (2020 to present)
- Solar and onshore wind market analysis primarily. Started covering offshore wind in 2023.
- Built Power BI dashboards on pipeline projects.
- Quarterly reports for the leadership team (Director level).

Tools:
Power BI, Advanced Excel, PowerPoint

Education:
BSc Energy Engineering, University of New South Wales (2020)
""",
)

add(
    "Rina Tan",
    "Shipping Market Analyst",
    """
rina.tan.demo@example.com  |  Singapore

Profile:
6 years in dry bulk and tanker shipping analysis. No offshore experience but strong
maritime domain knowledge.

Experience:

Senior Analyst — Asia Maritime Intelligence (2019 to present)
- Dry bulk freight rate forecasting and tanker demand modelling.
- Daily user of Clarkson Research.
- Excel-based modelling. Some PowerPoint for client reports.

Analyst — Southeast Asia Shipping Research (2017 to 2019)
- Tanker market analysis and competitor tracking.

Tools:
Clarkson Research, Advanced Excel, PowerPoint

Education:
BBA Maritime Business, Nanyang Technological University (2017)
""",
)

add(
    "Felix Adebayo",
    "Junior Renewables Analyst",
    """
felix.adebayo.demo@example.com  |  Lagos, Nigeria

Summary:
2-year analyst with offshore renewables exposure. Limited senior stakeholder time.

Experience:

Junior Analyst — West Africa Offshore Wind Initiative (2022 to present)
- Researches offshore wind feasibility studies for West African coast.
- Excel-based market sizing; PowerPoint reports to project managers.
- No direct exposure to VP/C-level audiences.

Intern — Maritime Strategy Group (2021 to 2022)
- Supported senior analysts on offshore renewables research.

Tools:
Excel, PowerPoint

Education:
BSc Economics, University of Lagos (2021)
""",
)

add(
    "Olga Petrov",
    "Ports Operations Analyst",
    """
olga.petrov.demo@example.com  |  Rotterdam, Netherlands

Profile:
7 years analysing ports operations and inland logistics. Some commercial-strategy
linkage but no offshore exposure.

Experience:

Operations Analyst — Rotterdam Port Solutions (2018 to present)
- Cargo throughput analysis, hinterland connection studies.
- Built Excel cost models that informed pricing decisions.
- Reports to operations director, occasional VP level.

Junior Analyst — Northern European Port Intelligence (2016 to 2018)
- Market sizing for European container port volumes.

Tools:
Excel, PowerPoint, basic Power BI

Education:
MSc Transport Economics, Erasmus University (2016)
""",
)

add(
    "Bryan O'Connell",
    "Energy Strategy Consultant",
    """
bryan.oconnell.demo@example.com  |  Dublin, Ireland

Summary:
Energy consultant with 9 years across upstream and midstream. No named offshore work
but solid analytical and commercial discipline.

Experience:

Senior Consultant — Atlantic Energy Advisors (2018 to present)
- Market entry studies for European energy clients.
- Built Excel financial models tied to investment decisions.
- Power BI dashboards for client deliverables.
- Frequent presentations to client executives.

Consultant — EuroEnergy Strategy (2015 to 2018)
- Onshore O&G market sizing and competitor analysis.

Tools:
Advanced Excel, Power BI, PowerPoint, basic Tableau

Education:
MBA, Trinity College Dublin (2015)
""",
)

add(
    "Sophia Russo",
    "Marketing Analyst | Maritime",
    """
sophia.russo.demo@example.com  |  Genoa, Italy

Profile:
5-year marketing-focused analyst at a maritime services group. Some market research
but primarily marketing campaign analytics.

Experience:

Marketing Analyst — Mediterranean Marine Services (2019 to present)
- Campaign performance analysis, customer segmentation.
- Some market research for new service launches.
- Excel and PowerPoint daily; occasional Power BI.

Tools:
Excel, PowerPoint, Power BI (intermediate)

Education:
BSc Marketing, Bocconi University (2019)
""",
)

add(
    "Mohammed Al-Rashid",
    "Tanker Shipping Analyst",
    """
mohammed.alrashid.demo@example.com  |  Dubai, UAE

Summary:
6 years tanker shipping analyst. Regular reporting to GM-level commercial leadership.

Experience:

Senior Analyst — Gulf Tanker Intelligence (2019 to present)
- VLCC and Suezmax freight rate analysis. Some OSV adjacency.
- Daily user of Clarkson Research and BIMCO data.
- Reports go to GM Commercial weekly.
- Advanced Excel and Power BI.

Tools:
Clarkson Research, BIMCO, Advanced Excel, Power BI, PowerPoint

Education:
MSc Shipping, Trade and Finance, Bayes Business School (2019)
""",
)

add(
    "Lucia Romano",
    "Renewable Energy Analyst",
    """
lucia.romano.demo@example.com  |  Madrid, Spain

Profile:
4-year analyst at a renewable energy firm. Mostly onshore but recent offshore wind work.

Experience:

Analyst — Iberian Renewables (2020 to present)
- Solar and onshore wind market analysis, with recent offshore wind coverage.
- Power BI dashboards used in board presentations to VP-level executives.
- Strong Excel modelling, PowerPoint for board materials.

Tools:
Power BI, Advanced Excel, PowerPoint

Education:
MSc Energy Engineering, ICAI Madrid (2020)
""",
)


# === WEAK MATCHES (expect Reject < 50) ===
add(
    "Tom Adams",
    "Senior Software Engineer",
    """
tom.adams.demo@example.com  |  Berlin, Germany

Summary:
10-year backend engineer building distributed systems. Looking to transition into
data-focused roles.

Experience:

Senior Software Engineer — TechCorp (2019 to present)
- Python and Go backend services on Kubernetes.
- Built internal data pipelines.

Software Engineer — StartupX (2015 to 2019)
- API development, microservices migration.

Tools:
Python, Go, Kubernetes, Docker, Postgres, Kafka

Education:
BSc Computer Science, TU Munich (2015)
""",
)

add(
    "Maya Singh",
    "Recent Economics Graduate",
    """
maya.singh.demo@example.com  |  Mumbai, India

Summary:
Recent economics graduate. No commercial work experience.

Education:
BA Economics, Delhi University (2025)
- Dissertation on Indian agricultural commodity markets.
- Coursework: econometrics, statistics, microeconomics.

Skills:
Excel (intermediate), Stata, R

Interests:
Commodity markets, market research.
""",
)

add(
    "Robert Chen",
    "Real Estate Analyst",
    """
robert.chen.demo@example.com  |  Hong Kong

Profile:
5-year real estate analyst at a property investment firm. No maritime/energy exposure.

Experience:

Senior Analyst — Hong Kong Property Partners (2020 to present)
- Commercial real estate market analysis.
- Excel valuation models, occasional PowerPoint pitch decks.

Tools:
Excel (advanced), Argus, PowerPoint

Education:
BSc Real Estate, HKU (2020)
""",
)

add(
    "Emma Roberts",
    "Marketing Coordinator",
    """
emma.roberts.demo@example.com  |  Toronto, Canada

Summary:
4 years in B2C marketing coordination. No analytical roles.

Experience:

Marketing Coordinator — Retail Brand Co (2021 to present)
- Campaign coordination, social media scheduling.
- Excel for tracking budgets.

Marketing Assistant — Consumer Goods Inc (2019 to 2021)
- Assisted in retail campaign execution.

Tools:
HubSpot, Mailchimp, Excel (basic)

Education:
BA Communications, University of Toronto (2019)
""",
)

add(
    "Hassan Yusuf",
    "Customer Service Lead",
    """
hassan.yusuf.demo@example.com  |  Cairo, Egypt

Summary:
Customer service professional at a logistics company. Operational role, no market work.

Experience:

Customer Service Lead — Cairo Logistics Group (2020 to present)
- Manages a team of 8 customer service agents.
- Resolves shipment exceptions and customer complaints.

Customer Service Agent — Express Cargo Egypt (2017 to 2020)
- Handled customer inquiries on parcel shipments.

Tools:
SAP, Zendesk

Education:
Diploma in Logistics, Cairo Institute (2017)
""",
)

add(
    "Lena Mueller",
    "Academic Researcher",
    """
lena.mueller.demo@example.com  |  Kiel, Germany

Profile:
PhD researcher in marine economics. Purely academic background, no commercial exposure.

Experience:

PhD Researcher — Kiel Institute for the World Economy (2020 to present)
- Research on maritime trade dynamics. Three published papers.
- No commercial or industry engagement.

Tools:
R, Stata, LaTeX

Education:
PhD candidate Maritime Economics, Christian-Albrechts University Kiel
MSc Economics, University of Kiel (2020)
""",
)

add(
    "Yuki Tanaka",
    "Financial Modeller | Banking",
    """
yuki.tanaka.demo@example.com  |  Tokyo, Japan

Summary:
Strong financial modelling background in investment banking. No offshore or maritime
exposure.

Experience:

Associate — Tokyo Investment Bank (2020 to present)
- Equity research on Japanese consumer sector.
- Advanced Excel + VBA modelling, PowerPoint pitch decks.

Analyst — Tokyo Investment Bank (2018 to 2020)
- Built financial models for M&A transactions.

Tools:
Advanced Excel (VBA), Bloomberg Terminal, PowerPoint

Education:
BCom Finance, Waseda University (2018)
""",
)

add(
    "Igor Volkov",
    "FMCG Senior Analyst",
    """
igor.volkov.demo@example.com  |  Warsaw, Poland

Profile:
Senior analyst in fast-moving consumer goods. No maritime/energy/offshore work.

Experience:

Senior Analyst — CEE Consumer Insights (2018 to present)
- Market sizing and competitor analysis for FMCG clients.
- Built Power BI dashboards used company-wide.
- Reports to VP Commercial monthly.

Analyst — Warsaw Market Research (2015 to 2018)
- Consumer trend reports.

Tools:
Power BI, Advanced Excel, PowerPoint, Nielsen retail panel data

Education:
MSc Marketing, Warsaw School of Economics (2015)
""",
)


# === EDGE CASES ===
add(
    "Daniel Park",
    "Market Analyst | Short Tenures",
    """
daniel.park.demo@example.com  |  Seoul, South Korea

Summary:
Strong analytical skills but each role under 12 months.

Experience:

Analyst — Korean Offshore Solutions (Jan 2025 to present, 5 months)
- Offshore OSV market analysis. Built Excel forecasting models.

Analyst — Asia Maritime Brokers (Mar 2024 to Dec 2024, 9 months)
- Tanker market reports.

Junior Analyst — Korean Shipping Intelligence (Jun 2023 to Feb 2024, 8 months)
- Dry bulk freight analysis.

Analyst Intern — Pacific Maritime Research (Sep 2022 to May 2023, 8 months)
- Supported senior analysts.

Tools:
Clarkson Research, Advanced Excel, Power BI, PowerPoint

Education:
BBA International Trade, Seoul National University (2022)
""",
)

add(
    "Nadia Khan",
    "Junior Market Analyst",
    """
nadia.khan.demo@example.com  |  Karachi, Pakistan

Summary:
3-year analyst — lists many tools without demonstrated usage in role descriptions.

Experience:

Market Analyst — Indus Energy Intelligence (2022 to present)
- Energy market reports for South Asian clients.

Junior Analyst — Karachi Trade Research (2021 to 2022)
- Trade flow analysis.

Skills (self-declared):
Proficient in Power BI. Advanced Excel. Tableau. Python. Rystad Energy. Clarkson Research.
Bloomberg Terminal. PowerPoint. IHS Markit. Familiar with S&P Global. SAP Business Objects.

Education:
BSc Economics, LUMS (2021)
""",
)


# Note: I omit a scanned-PDF decoy here because fpdf2 always embeds text;
# adding image-only PDFs would need a different toolchain (skipped for the demo set).


# Fill remaining slots (extra strong + mid for diversity to reach 30)

add(
    "Henrik Larsen",
    "Offshore Drilling Commercial Analyst",
    """
henrik.larsen.demo@example.com  |  Copenhagen, Denmark

Profile:
6 years in offshore drilling commercial analysis. Direct line to senior strategy team.

Experience:

Commercial Analyst — Nordic Drilling AS (2019 to present)
- Day-rate and utilisation forecasting for jackups and semi-subs.
- Built Excel models that fed two USD 90M asset deployment decisions.
- Reports to VP Strategy quarterly.
- Daily user of Rystad Energy and IHS Markit.

Analyst — Scandinavian Energy Research (2017 to 2019)
- Offshore rig market reports for Northern European clients.

Tools:
Rystad Energy, IHS Markit, Advanced Excel, Power BI, PowerPoint

Education:
MSc Finance, Copenhagen Business School (2017)
""",
)

add(
    "Fatima Hassan",
    "Cargo & Ports Forecasting Analyst",
    """
fatima.hassan.demo@example.com  |  Doha, Qatar

Summary:
5-year analyst at a Middle East logistics group. Recent offshore exposure.

Experience:

Senior Analyst — Qatar Logistics Holdings (2020 to present)
- Cargo throughput forecasting and ports demand modelling.
- Recently expanded scope to include offshore service vessel demand from Qatari NOCs.
- Built IHS Markit-fed Power BI dashboards used by Business Development.
- Quarterly briefings to VP Business Development.

Analyst — Middle East Trade Intelligence (2018 to 2020)
- Trade flow analysis for MENA region.

Tools:
IHS Markit, Advanced Excel, Power BI, PowerPoint

Education:
MSc International Logistics, Qatar University (2018)
""",
)

add(
    "Jack Whitmore",
    "Junior Offshore Wind Market Researcher",
    """
jack.whitmore.demo@example.com  |  Edinburgh, UK

Summary:
1-year junior market researcher transitioning from academia. Strong methodology but
limited stakeholder exposure.

Experience:

Junior Researcher — Edinburgh Offshore Wind Forum (2024 to present)
- Researches floating offshore wind market dynamics in UK & Norway.
- Builds Excel-based pipeline tracking models.

Research Assistant — University of Edinburgh (2022 to 2024)
- Academic research on offshore renewables.

Tools:
Excel, PowerPoint, Python (academic)

Education:
MSc Sustainable Energy Systems, University of Edinburgh (2024)
""",
)

# Total count check would be done after the loop below.


def main():
    print(f"Generating {len(CVS)} sample CVs to {OUT_DIR}/")
    for idx, cv in enumerate(CVS, start=1):
        file_name = f"{idx:02d}_{slug(cv['name'])}.pdf"
        header = f"{cv['name']}\n{cv['headline']}\n"
        render_pdf(cv["name"], header + cv["body"], file_name)
        print(f"  {file_name}")
    print(f"Done. {len(CVS)} files written to {OUT_DIR}")


if __name__ == "__main__":
    main()
