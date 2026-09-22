"""Proofreading workbook: every extracted fact in one spreadsheet.

Reads web/weeks.json and web/details.json (so run `build` first) and writes
proofread.xlsx: one tab per kind of data, each row linked to the Wikipedia
revision it came from, with two yellow columns for the reader to fill in.
Player totals are COUNTIFS formulas over the Weeks and Votes tabs, so a
correction typed into those tabs flows through.
"""
import json
import re
import zipfile
from datetime import date
from xml.sax.saxutils import escape

from openpyxl import Workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from .config import ROOT, WEB_DIR

FONT = "Arial"
HEADER_FILL = PatternFill("solid", fgColor="1F2937")
INPUT_FILL = PatternFill("solid", fgColor="FFF2CC")  # cells the reader fills in
NOTE_FILL = PatternFill("solid", fgColor="FDF6E3")
CHECKS = ["Looks right?", "Correction"]
CHOICES = '"OK,Wrong,Unsure"'


def _key(names):
    """Names as ";a;b;" so COUNTIFS can match whole names ("*;Nicole A.;*").

    ";" rather than "|": some formula engines turn wildcards into regular
    expressions without escaping, where "|" means "or".
    """
    return ";" + ";".join(names) + ";" if names else ""


def _join(names):
    return ", ".join(names)


def _veto_text(rnd, veto):
    if not veto:
        return ""
    parts = []
    if not veto["used"]:
        parts.append("Not used")
    else:
        on = _join(veto["on"])
        parts.append(f"Used on {on}" + (" (themselves)" if veto["on"] == rnd["veto_winners"] else ""))
        if veto["replacements"]:
            parts.append(f"replacement: {_join(veto['replacements'])}")
    if veto["twist_saved"]:
        parts.append(f"{_join(veto['twist_saved'])} saved by a twist")
    return "; ".join(parts)


def _tally_text(t):
    if not t:
        return ""
    if t["type"] == "vote":
        return f"{t['votes_to_evict']} of {t['votes_cast']} votes to evict"
    return f"{t['by']}'s choice to evict"


def _store_cached_values(path, sheetnames, values):
    """Fill in formula cells' cached results, which openpyxl leaves empty.

    Excel and Google Sheets recalculate on open anyway (the workbook sets
    fullCalcOnLoad), but previewers that don't calculate, like the iPhone
    Files preview, show only cached results. values: {sheet: {"D2": 3}}.
    tests/test_proofread.py checks these against a formula engine.
    """
    with zipfile.ZipFile(path) as z:
        parts = {name: z.read(name) for name in z.namelist()}
    for index, title in enumerate(sheetnames, 1):
        cells = values.get(title)
        if not cells:
            continue
        name = f"xl/worksheets/sheet{index}.xml"
        xml = parts[name].decode("utf-8")

        def fill(m):
            v = cells.get(m.group(1))
            if v is None:
                return m.group(0)
            attrs = m.group(2) + ('' if isinstance(v, (int, float)) else ' t="str"')
            return f'<c r="{m.group(1)}"{attrs}><f>{m.group(3)}</f><v>{escape(str(v))}</v></c>'
        xml = re.sub(r'<c r="([A-Z]+\d+)"([^>]*)><f>(.*?)</f><v></v></c>', fill, xml)
        parts[name] = xml.encode("utf-8")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in parts.items():
            z.writestr(name, data)


def _sheet(wb, title, headers, widths, rows, links=None, wrap=(), hidden=(), note_col=None,
           source_label="Wikipedia"):
    """Write a table with a styled header, filters, frozen panes and input columns."""
    ws = wb.create_sheet(title)
    ws.append(headers)
    for c, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=c)
        cell.font = Font(name=FONT, bold=True, color="FFFFFF")
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    for r, row in enumerate(rows, 2):
        for c, value in enumerate(row, 1):
            cell = ws.cell(row=r, column=c, value=value)
            cell.font = Font(name=FONT, size=10)
            cell.alignment = Alignment(vertical="top", wrap_text=headers[c - 1] in wrap)
        if links:
            url = links[r - 2]
            if url:
                cell = ws.cell(row=r, column=headers.index("Source") + 1, value=source_label)
                cell.hyperlink = url
                cell.font = Font(name=FONT, size=10, color="0563C1", underline="single")
    for name in CHECKS:
        col = headers.index(name) + 1
        for r in range(2, len(rows) + 2):
            ws.cell(row=r, column=col).fill = INPUT_FILL
    last = len(rows) + 1
    dv = DataValidation(type="list", formula1=CHOICES, allow_blank=True)
    dv.add(f"{get_column_letter(headers.index('Looks right?') + 1)}2:"
           f"{get_column_letter(headers.index('Looks right?') + 1)}{max(last, 2)}")
    ws.add_data_validation(dv)
    for c, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(c)].width = w
    for name in hidden:
        ws.column_dimensions[get_column_letter(headers.index(name) + 1)].hidden = True
    if note_col:  # shade rows whose status isn't ok
        col = get_column_letter(headers.index(note_col) + 1)
        ws.conditional_formatting.add(
            f"A2:{get_column_letter(len(headers))}{max(last, 2)}",
            FormulaRule(formula=[f'AND(${col}2<>"",${col}2<>"ok")'], fill=NOTE_FILL))
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{max(last, 1)}"
    return ws


def build(web_dir=WEB_DIR, out=ROOT / "proofread.xlsx"):
    weeks_doc = json.loads((web_dir / "weeks.json").read_text(encoding="utf-8"))
    details = json.loads((web_dir / "details.json").read_text(encoding="utf-8"))
    sources = {s["season"]: s.get("permalink") or s["url"] for s in weeks_doc["sources"]}
    fandom_sources = {s["season"]: s["fandom"].get("permalink") or s["fandom"]["url"]
                      for s in weeks_doc["sources"] if s.get("fandom")}
    weeks = sorted(weeks_doc["weeks"], key=lambda w: (-w["season"], w["week"] or 999))

    def src(season, anchor="Voting_history"):
        return f"{sources[season]}#{anchor}" if season in sources else None

    def fsrc(season, anchor):
        return f"{fandom_sources[season]}#{anchor}" if season in fandom_sources else None

    wb = Workbook()
    readme = wb.active
    readme.title = "Read me"

    # --- Weeks: one row per round (or per week when nothing was modeled) ---
    wk_headers = ["Season", "Week", "Round", "Status", "Note", "HOH", "HOH comp", "Noms", "Veto",
                  "Veto comp", "Veto use", "Twist rows", "Final noms", "Evicted", "Tally",
                  "Source", *CHECKS, "hoh_key", "veto_key", "noms_key", "final_key", "twist_key"]
    wk_rows, wk_links = [], []
    for w in weeks:
        d = details["weeks"].get(f"{w['season']}|{w['week_label']}", {})
        comps = [c for c in d.get("comps", []) if c["winner"]]
        rounds = w["rounds"] or [None]
        for i, rnd in enumerate(rounds):
            if rnd is None:
                wk_rows.append([f"BB{w['season']}", w["week_label"], "", w["status"], w["note"],
                                *[""] * 10, None, "", "", "", "", "", "", ""])
                wk_links.append(src(w["season"]))
                continue
            comp = {c["kind"]: c["name"] for c in comps if c["round"] == i + 1}
            # The Big Brother Wiki's Competition History wins over the episode summaries.
            comp.update({c["kind"]: c["name"] for c in reversed((d.get("fandom") or {}).get("comps", []))
                         if c["round"] == i + 1 and c["name"] and c["kind"] in ("hoh", "veto")})
            twist_names = [n for names in rnd["extras"].values() for n in names
                           if not (n.startswith("(") and n.endswith(")"))]
            veto = (d.get("rounds") or [{}] * len(rounds))[i].get("veto")
            wk_rows.append([
                f"BB{w['season']}", w["week_label"], rnd["sub_label"] or "", w["status"], w["note"] or "",
                _join(rnd["hoh"]), comp.get("hoh", ""), _join(rnd["nominees_initial"]),
                _join(rnd["veto_winners"]), comp.get("veto", ""), _veto_text(rnd, veto),
                "; ".join(f"{k}: {_join(v)}" for k, v in rnd["extras"].items()),
                _join(rnd["nominees_final"]), rnd["evicted"] or "", _tally_text(rnd["tally"]),
                None, "", "",
                _key(rnd["hoh"]), _key(rnd["veto_winners"]), _key(rnd["nominees_initial"]),
                _key(rnd["nominees_final"]), _key(twist_names),
            ])
            wk_links.append(src(w["season"]))
    _sheet(wb, "Weeks", wk_headers,
           [8, 9, 9, 7, 30, 16, 18, 24, 16, 18, 30, 26, 20, 12, 22, 11, 12, 30, 1, 1, 1, 1, 1],
           wk_rows, wk_links, wrap={"Note", "Noms", "Veto use", "Twist rows", "Correction"},
           hidden=("hoh_key", "veto_key", "noms_key", "final_key", "twist_key"), note_col="Status")

    # --- Votes: one row per houseguest per round ---
    vt_headers = ["Season", "Week", "Round", "Voter", "Voted to evict", "Didn't vote because",
                  "Evicted", "With the house", "Source", *CHECKS]
    vt_rows, vt_links = [], []
    for w in weeks:
        d = details["weeks"].get(f"{w['season']}|{w['week_label']}", {})
        for i, (rnd, v) in enumerate(zip(w["rounds"], d.get("rounds", []))):
            r = len(vt_rows) + 2
            for vote in v["votes"]:
                vt_rows.append([f"BB{w['season']}", w["week_label"], rnd["sub_label"] or "", vote["voter"],
                                vote["vote"], "", rnd["evicted"] or "", None, None, "", ""])
            for nv in v["not_voting"]:
                vt_rows.append([f"BB{w['season']}", w["week_label"], rnd["sub_label"] or "", nv["voter"],
                                "", nv["reason"], rnd["evicted"] or "", None, None, "", ""])
            vt_links += [src(w["season"])] * (len(vt_rows) + 2 - r)
    cached = {"Votes": {}, "Players": {}}
    for r, row in enumerate(vt_rows, 2):
        cached["Votes"][f"H{r}"] = "" if not row[4] else ("Yes" if row[4] == row[6] else "No")
        row[7] = f'=IF(E{r}="","",IF(E{r}=G{r},"Yes","No"))'
    _sheet(wb, "Votes", vt_headers, [8, 9, 9, 14, 16, 22, 14, 14, 11, 12, 30], vt_rows, vt_links)

    # --- Players: totals are formulas over Weeks and Votes ---
    pl_headers = ["Season", "Player", "Result", "HOHs", "Vetoes", "Twist wins", "Noms", "Final noms",
                  "Votes against", "Votes cast", "With the house", "Source", *CHECKS]
    col = {h: get_column_letter(wk_headers.index(h) + 1) for h in wk_headers}
    players = sorted(details["players"], key=lambda p: -p["season"])
    wl, vl = len(wk_rows) + 1, len(vt_rows) + 1  # last data row on Weeks / Votes

    def wk(c):
        return f"Weeks!${c}$2:${c}${wl}"

    def vt(c):
        return f"Votes!${c}$2:${c}${vl}"
    pl_rows = []
    for r, p in enumerate(players, 2):
        totals = [len(p["hoh"]), len(p["veto"]), len(p["twist"]), len(p["nominated"]), len(p["on_block"]),
                  sum(len(v["voters"]) for v in p["votes_against"]), len(p["votes_cast"]),
                  sum(v["with_house"] for v in p["votes_cast"])]
        cached["Players"].update({f"{get_column_letter(4 + i)}{r}": t for i, t in enumerate(totals)})
        def weeks_count(key_col):
            return f'=COUNTIFS({wk("A")},$A{r},{wk(col[key_col])},"*;"&$B{r}&";*")'
        pl_rows.append([
            f"BB{p['season']}", p["name"], p["result"] or "In the game",
            weeks_count("hoh_key"), weeks_count("veto_key"), weeks_count("twist_key"),
            weeks_count("noms_key"), weeks_count("final_key"),
            f"=COUNTIFS({vt('A')},$A{r},{vt('E')},$B{r})",
            f"=COUNTIFS({vt('A')},$A{r},{vt('D')},$B{r},{vt('E')},\"<>\")",
            f"=COUNTIFS({vt('A')},$A{r},{vt('D')},$B{r},{vt('H')},\"Yes\")",
            None, "", "",
        ])
    _sheet(wb, "Players", pl_headers, [8, 14, 18, 7, 7, 9, 7, 9, 9, 9, 10, 11, 12, 30], pl_rows,
           [src(p["season"], "HouseGuests") for p in players])

    # --- Competitions found in the episode summaries ---
    cp_headers = ["Season", "Week", "Kind", "Competition", "Won by", "Round", "From the summary", "Source",
                  *CHECKS]
    cp_rows, cp_links = [], []
    for w in weeks:
        d = details["weeks"].get(f"{w['season']}|{w['week_label']}", {})
        for c in d.get("comps", []):
            cp_rows.append([f"BB{w['season']}", w["week_label"], c["kind"].upper() if c["kind"] == "hoh" else "Veto",
                            c["name"], c["winner"] or "(not tied to a winner)",
                            c["round"] or "", c["source"], None, "", ""])
            cp_links.append(src(w["season"], "Episodes"))
    _sheet(wb, "Competitions", cp_headers, [8, 9, 7, 26, 20, 7, 60, 11, 12, 30], cp_rows, cp_links,
           wrap={"From the summary", "Correction"})

    # --- Big Brother Wiki (Fandom): every competition, Have-Nots, bios, disagreements ---
    fc_headers = ["Season", "Week", "Day", "Type", "Competition", "Format", "Result", "Round", "Source", *CHECKS]
    fc_rows, fc_links, hn_rows, hn_links, dg_rows, dg_links = [], [], [], [], [], []
    for w in weeks:
        f = details["weeks"].get(f"{w['season']}|{w['week_label']}", {}).get("fandom")
        if not f:
            continue
        for c in f["comps"]:
            fc_rows.append([f"BB{w['season']}", w["week_label"], c["day"] or "", c["type"], c["name"] or "",
                            c["format"] or "", " & ".join(c["winners"]) + (" " if c["winners"] else "") + c["outcome"],
                            c["round"] or "", None, "", ""])
            fc_links.append(fsrc(w["season"], "Competition_History"))
        for h in f["have_nots"]:
            hn_rows.append([f"BB{w['season']}", w["week_label"], h["name"], h["chosen_by"] or "", None, "", ""])
            hn_links.append(fsrc(w["season"], "Have/Have-Not_History"))
        for c in f["checks"]:
            dg_rows.append([f"BB{w['season']}", w["week_label"], c["round"], c["field"], _join(c["wikipedia"]),
                            _join(c["fandom"]), None, "", ""])
            dg_links.append(fsrc(w["season"], "Game_History"))
    _sheet(wb, "BB Wiki comps", fc_headers, [8, 9, 7, 18, 26, 20, 30, 7, 11, 12, 30], fc_rows, fc_links,
           wrap={"Result", "Correction"}, source_label="BB Wiki")
    _sheet(wb, "Have-Nots", ["Season", "Week", "Have-Not", "Made a Have-Not by", "Source", *CHECKS],
           [8, 9, 16, 20, 11, 12, 30], hn_rows, hn_links, source_label="BB Wiki")
    bio_headers = ["Season", "Player", "Full name", "Age at premiere", "Born", "Hometown", "Occupation",
                   "Days", "Alliances", "Source", *CHECKS]
    bio_rows, bio_links = [], []
    for p in players:
        f = p.get("fandom")
        if not f:
            continue
        bio_rows.append([f"BB{p['season']}", p["name"], f.get("full_name") or "", f.get("age"),
                         date.fromisoformat(f["birth_date"]) if f.get("birth_date") else "",
                         " / ".join(f.get("hometown") or []), f.get("occupation") or "", f.get("days") or "",
                         ", ".join(f.get("alliances") or []), None, "", ""])
        bio_links.append(f.get("url"))
    ws = _sheet(wb, "Bios", bio_headers, [8, 14, 24, 9, 12, 26, 26, 6, 40, 11, 12, 30], bio_rows, bio_links,
                wrap={"Alliances", "Correction"}, source_label="BB Wiki")
    for r in range(2, len(bio_rows) + 2):
        ws.cell(row=r, column=5).number_format = "mmm d, yyyy"
    _sheet(wb, "Sources disagree", ["Season", "Week", "Round", "Field", "Wikipedia", "Big Brother Wiki", "Source",
                                    *CHECKS],
           [8, 9, 7, 18, 30, 30, 11, 12, 30], dg_rows, dg_links, wrap={"Wikipedia", "Big Brother Wiki", "Correction"},
           source_label="BB Wiki")

    # --- What was different: twist rows, unusual outcomes, Wikipedia notes ---
    nt_headers = ["Season", "Week", "Type", "Text", "Source", *CHECKS]
    nt_rows, nt_links = [], []
    for w in weeks:
        d = details["weeks"].get(f"{w['season']}|{w['week_label']}", {})
        sp = d.get("special", {"items": [], "notes": []})
        for item in sp["items"]:
            nt_rows.append([f"BB{w['season']}", w["week_label"], "Twist / outcome", item, None, "", ""])
            nt_links.append(src(w["season"]))
        for n in sp["notes"]:
            nt_rows.append([f"BB{w['season']}", w["week_label"], f"Wikipedia note [{n['label']}]", n["text"],
                            None, "", ""])
            nt_links.append(src(w["season"]))
        for v in d.get("veto_notes", []):
            nt_rows.append([f"BB{w['season']}", w["week_label"], "Veto (episode summary)", v, None, "", ""])
            nt_links.append(src(w["season"], "Episodes"))
    _sheet(wb, "What was different", nt_headers, [8, 9, 20, 80, 11, 12, 30], nt_rows, nt_links,
           wrap={"Text", "Correction"})

    # --- Episodes ---
    ep_headers = ["Season", "Week", "No. overall", "No.", "Title", "Days", "Air date", "Viewers (M)",
                  "Summary", "Source", *CHECKS]
    ep_rows, ep_links = [], []
    for w in weeks:
        d = details["weeks"].get(f"{w['season']}|{w['week_label']}", {})
        for e in d.get("episodes", []):
            air = date.fromisoformat(e["air_date"]) if e["air_date"] else (e["air_date_text"] or "")
            ep_rows.append([f"BB{w['season']}", w["week_label"], e["number_overall"], e["number"], e["title"],
                            e["days"] or "", air, e["viewers_millions"], e["summary"] or "", None, "", ""])
            ep_links.append(src(w["season"], "Episodes"))
    ws = _sheet(wb, "Episodes", ep_headers, [8, 9, 9, 6, 12, 14, 12, 9, 90, 11, 12, 30], ep_rows, ep_links,
                wrap={"Summary", "Correction"})
    for r in range(2, len(ep_rows) + 2):
        ws.cell(row=r, column=7).number_format = "mmm d, yyyy"

    # --- Read me ---
    lines = [
        ("Big Brother data: proofreading sheet", True),
        (f"Generated {weeks_doc['generated_at']} from the Wikipedia and Big Brother Wiki pages cached in this "
         f"repo (data: Wikipedia, CC BY-SA 4.0; Big Brother Wiki, CC BY-SA 3.0).", False),
        ("", False),
        ("How to proofread", True),
        ("Only the yellow columns are for you: set “Looks right?” to OK, Wrong or Unsure, "
         "and write what should change in “Correction”.", False),
        ("Example: on Weeks, BB26 · Week 4, you might set Wrong and write "
         "“Veto use should say Tucker used it on himself”.", False),
        ("Every row has a Source link to the exact revision the data came from: Wikipedia, or the "
         "Big Brother Wiki (bigbrother.fandom.com) on the BB Wiki tabs.", False),
        ("Filters are on every header row; shaded Weeks rows are weeks that aren’t plain evictions.", False),
        ("", False),
        ("Tabs", True),
        (f"Weeks ({len(wk_rows)} rows): one row per eviction round — HOH, noms, veto, twist rows, "
         "final noms, evicted, tally, plus the HOH/veto competition names and what the veto did.", False),
        (f"Votes ({len(vt_rows)} rows): every houseguest’s vote in every round, or why they didn’t vote. "
         "“With the house” is a formula.", False),
        (f"Players ({len(pl_rows)} rows): totals are COUNTIFS formulas over Weeks and Votes, "
         "so fixing a week there updates them.", False),
        (f"Competitions ({len(cp_rows)} rows): competition names found in the episode summaries, "
         "with the sentence each came from.", False),
        (f"BB Wiki comps ({len(fc_rows)} rows): every competition in the Big Brother Wiki’s Competition "
         "History, twists included. Round is the round whose HOH or veto winner it matches.", False),
        (f"Have-Nots ({len(hn_rows)} rows): each week’s Have-Nots and, where the wiki says, who picked them.", False),
        (f"Bios ({len(bio_rows)} rows): full name, age at the premiere, hometown and occupation from each "
         "houseguest’s Big Brother Wiki page.", False),
        (f"Sources disagree ({len(dg_rows)} rows): where the Big Brother Wiki’s Game History differs from "
         "Wikipedia. The site follows Wikipedia.", False),
        (f"What was different ({len(nt_rows)} rows): twist rows, unusual outcomes, Wikipedia’s notes, "
         "and the episode summaries’ veto-meeting lines.", False),
        (f"Episodes ({len(ep_rows)} rows): every episode with days, air date, viewers and summary.", False),
        ("", False),
        ("Derived, not stated in Wikipedia’s table", True),
        ("Veto use: worked out from the noms before and after the veto.", False),
        ("Competition names: from the Big Brother Wiki’s Competition History, or else matched from the "
         "episode summaries (tied to a winner only when the summary names them nearby).", False),
        ("Player totals: count only the rounds the grid models (twist rounds shown as notes are left out).",
         False),
    ]
    readme.column_dimensions["A"].width = 110
    for r, (text, bold) in enumerate(lines, 1):
        cell = readme.cell(row=r, column=1, value=text)
        cell.font = Font(name=FONT, bold=bold, size=14 if r == 1 else 11)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    readme.cell(row=5, column=1).fill = INPUT_FILL

    wb.save(out)
    _store_cached_values(out, wb.sheetnames, cached)
    return out, {"weeks": len(wk_rows), "votes": len(vt_rows), "players": len(pl_rows),
                 "competitions": len(cp_rows), "notes": len(nt_rows), "episodes": len(ep_rows),
                 "bb_wiki_comps": len(fc_rows), "have_nots": len(hn_rows), "bios": len(bio_rows),
                 "disagreements": len(dg_rows)}
