#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

XLSX_CANDIDATES = ["gantt.xlsx", "gantt_detaille.xlsx"]
OWNER = "ryantsou"
REPO = "AKIMBOT"
PROJECT_NUMBER = "2"

NS_MAIN = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


@dataclass
class Task:
    raw_id: str
    phase: str
    microtask: str
    resp: str


def normalize(text: str) -> str:
    text = (text or "").strip().lower()
    text = "".join(ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^a-z0-9\s#-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def phase_slug(text: str) -> str:
    base = normalize(text)
    base = base.replace(" ", "-")
    base = re.sub(r"-+", "-", base).strip("-")
    return base[:48] or "phase"


def pick_xlsx_path() -> str:
    for candidate in XLSX_CANDIDATES:
        if os.path.exists(candidate):
            return candidate
    raise RuntimeError(
        "Aucun fichier Gantt trouvé. Noms attendus: " + ", ".join(XLSX_CANDIDATES)
    )


def col_to_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    idx = 0
    for ch in letters:
        idx = idx * 26 + (ord(ch.upper()) - ord("A") + 1)
    return idx - 1


def read_shared_strings(zf: zipfile.ZipFile) -> List[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    out = []
    for si in root.findall("a:si", NS_MAIN):
        parts = [t.text or "" for t in si.findall(".//a:t", NS_MAIN)]
        out.append("".join(parts))
    return out


def cell_text(cell: ET.Element, shared: List[str]) -> str:
    ctype = cell.attrib.get("t")
    v = cell.find("a:v", NS_MAIN)
    if ctype == "s" and v is not None and v.text is not None:
        i = int(v.text)
        return shared[i] if 0 <= i < len(shared) else ""
    if ctype == "inlineStr":
        is_el = cell.find("a:is", NS_MAIN)
        if is_el is not None:
            return "".join(t.text or "" for t in is_el.findall(".//a:t", NS_MAIN))
    if v is not None and v.text is not None:
        return v.text
    return ""


def find_sheet_path(zf: zipfile.ZipFile) -> str:
    workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))

    ns_rel = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}
    target_rel_id = None
    for sheet in workbook.findall("a:sheets/a:sheet", NS_MAIN):
        name = (sheet.attrib.get("name") or "").lower()
        if "gantt" in name:
            target_rel_id = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            break
    if not target_rel_id:
        first_sheet = workbook.find("a:sheets/a:sheet", NS_MAIN)
        if first_sheet is None:
            raise RuntimeError("Le classeur Excel ne contient aucune feuille exploitable.")
        target_rel_id = first_sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")

    for rel in rels.findall("r:Relationship", ns_rel):
        if rel.attrib.get("Id") == target_rel_id:
            target = rel.attrib.get("Target", "")
            return "xl/" + target.lstrip("/")

    raise RuntimeError("Impossible de localiser la feuille Gantt dans le fichier XLSX.")


def header_map_from_row(cells: Dict[int, str]) -> Dict[str, int]:
    aliases: Dict[str, List[str]] = {
        "id": ["#", "id", "numero", "n"],
        "phase": ["phase"],
        "microtask": ["micro tache", "micro-tache", "micro tache", "micro-tâche", "tache", "task"],
        "resp": ["resp", "resp.", "responsable", "responsables", "owner"],
    }

    norm_by_idx = {idx: normalize(txt) for idx, txt in cells.items() if txt and normalize(txt)}
    out: Dict[str, int] = {}
    for logical_name, options in aliases.items():
        opts = {normalize(o) for o in options}
        for idx, norm_txt in norm_by_idx.items():
            if norm_txt in opts:
                out[logical_name] = idx
                break

    missing = [k for k in ["id", "phase", "microtask", "resp"] if k not in out]
    if missing:
        raise RuntimeError(
            "Colonnes manquantes dans l'en-tête Gantt: " + ", ".join(missing)
        )
    return out


def extract_tasks(path: str) -> List[Task]:
    with zipfile.ZipFile(path) as zf:
        shared = read_shared_strings(zf)
        sheet_xml = zf.read(find_sheet_path(zf))
        root = ET.fromstring(sheet_xml)
        rows = root.findall(".//a:sheetData/a:row", NS_MAIN)

        tasks: List[Task] = []
        pattern = re.compile(r"^#\d+$")
        mapping: Optional[Dict[str, int]] = None

        for row in rows:
            cells = {}
            for c in row.findall("a:c", NS_MAIN):
                ref = c.attrib.get("r", "")
                idx = col_to_index(ref)
                cells[idx] = cell_text(c, shared)

            row_num = int(row.attrib.get("r", "0") or "0")
            if mapping is None and row_num >= 2:
                try:
                    mapping = header_map_from_row(cells)
                    continue
                except RuntimeError:
                    continue

            if mapping is None:
                continue

            raw_id = (cells.get(mapping["id"], "") or "").strip()
            if not pattern.match(raw_id):
                continue

            phase = (cells.get(mapping["phase"], "") or "").strip()
            microtask = (cells.get(mapping["microtask"], "") or "").strip()
            resp = (cells.get(mapping["resp"], "") or "").strip()
            if not microtask:
                continue
            tasks.append(Task(raw_id=raw_id, phase=phase, microtask=microtask, resp=resp))

        tasks.sort(key=lambda x: int(x.raw_id[1:]))
        return tasks


def run_checked(cmd: List[str], operation: str) -> Dict:
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        err = (res.stderr or "").strip() or (res.stdout or "").strip()
        raise RuntimeError(f"{operation} a échoué: {err}")
    return json.loads(res.stdout or "{}")


def get_existing_project_titles() -> List[str]:
    cmd = [
        "gh",
        "project",
        "item-list",
        PROJECT_NUMBER,
        "--owner",
        OWNER,
        "--limit",
        "500",
        "--format",
        "json",
    ]
    payload = run_checked(cmd, "La récupération des items du project")
    items = payload.get("items", []) if isinstance(payload, dict) else payload
    titles = []
    for it in items:
        title = (it or {}).get("title")
        if not title and isinstance((it or {}).get("content"), dict):
            title = it["content"].get("title")
        if title:
            titles.append(title)
    return titles


def get_existing_issue_titles() -> List[str]:
    cmd = [
        "gh",
        "issue",
        "list",
        "--repo",
        f"{OWNER}/{REPO}",
        "--state",
        "all",
        "--limit",
        "500",
        "--json",
        "title",
    ]
    payload = run_checked(cmd, "La récupération des issues")
    return [it.get("title", "") for it in payload if it.get("title")]


def ensure_label(name: str, color: str, description: str) -> None:
    cmd = [
        "gh",
        "label",
        "create",
        name,
        "--repo",
        f"{OWNER}/{REPO}",
        "--color",
        color,
        "--description",
        description,
        "--force",
    ]
    subprocess.run(cmd, capture_output=True, text=True)


def issue_title(task: Task) -> str:
    return f"{task.raw_id} - {task.microtask}"


def issue_body(task: Task, source_file: str) -> str:
    phase_line = task.phase or "Phase non précisée"
    resp_line = task.resp or "Non défini"
    return (
        f"### Contexte\n"
        f"Micro-tâche issue du planning Gantt de l'équipe.\n\n"
        f"### Détails\n"
        f"- Phase: {phase_line}\n"
        f"- Responsable(s): {resp_line}\n"
        f"- Source: {source_file}\n\n"
        f"### Définition de terminé\n"
        f"- [ ] Développement effectué\n"
        f"- [ ] Vérification locale faite\n"
        f"- [ ] PR ouverte avec une description claire\n"
    )


def create_issue(task: Task, source_file: str) -> Tuple[str, str]:
    title = issue_title(task)
    body = issue_body(task, source_file)
    labels = ["micro-tache", f"phase:{phase_slug(task.phase)}"]

    cmd = [
        "gh",
        "issue",
        "create",
        "--repo",
        f"{OWNER}/{REPO}",
        "--title",
        title,
        "--body",
        body,
    ]
    for label in labels:
        cmd.extend(["--label", label])

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        err = (res.stderr or "").strip() or (res.stdout or "").strip()
        raise RuntimeError(err)

    url = (res.stdout or "").strip().splitlines()[-1]
    return title, url


def add_url_to_project(url: str) -> bool:
    cmd = [
        "gh",
        "project",
        "item-add",
        PROJECT_NUMBER,
        "--owner",
        OWNER,
        "--url",
        url,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        err = (res.stderr or "").strip() or (res.stdout or "").strip()
        if "already exists in this project" in err.lower():
            return False
        raise RuntimeError(err)
    return True


def ensure_phase_markers(phases: List[str], existing_project_norm: Set[str]) -> List[str]:
    created: List[str] = []
    for phase in phases:
        marker_title = f"PHASE | {phase}"
        if normalize(marker_title) in existing_project_norm:
            continue

        body = "Repère visuel pour regrouper les micro-tâches de cette phase."
        cmd = [
            "gh",
            "project",
            "item-create",
            PROJECT_NUMBER,
            "--owner",
            OWNER,
            "--title",
            marker_title,
            "--body",
            body,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            created.append(marker_title)
            existing_project_norm.add(normalize(marker_title))
    return created


def build_phase_color(phase: str) -> str:
    palette = [
        "1f6feb",
        "238636",
        "bf8700",
        "8250df",
        "d1242f",
        "0969da",
        "0a7f5a",
        "9a6700",
    ]
    return palette[hash(phase_slug(phase)) % len(palette)]


def main() -> int:
    xlsx_path = pick_xlsx_path()
    gantt_tasks = extract_tasks(xlsx_path)
    existing_project_norm = {normalize(t) for t in get_existing_project_titles()}
    existing_issue_norm = {normalize(t) for t in get_existing_issue_titles()}

    ensure_label("micro-tache", "0969da", "Issue issue du Gantt détaillé")

    unique_phases = [t.phase for t in gantt_tasks if t.phase]
    unique_phases = sorted(set(unique_phases))
    for phase in unique_phases:
        ensure_label(
            f"phase:{phase_slug(phase)}",
            build_phase_color(phase),
            f"Micro-tâches de la phase {phase}",
        )

    phase_markers = ensure_phase_markers(unique_phases, existing_project_norm)

    already_present = 0
    created_issues: List[str] = []
    already_in_project = 0
    failed: List[Tuple[str, str]] = []

    print(f"Synchronisation en cours pour {len(gantt_tasks)} tâches... (cela peut prendre quelques minutes)")

    for task in gantt_tasks:
        title = issue_title(task)
        ntitle = normalize(title)
        if ntitle in existing_issue_norm:
            already_present += 1
            continue

        try:
            created_title, issue_url = create_issue(task, xlsx_path)
            added_to_project = add_url_to_project(issue_url)
            if not added_to_project:
                already_in_project += 1
            created_issues.append(created_title)
            existing_issue_norm.add(ntitle)
            print(f"[+] Créé : {title}")
        except RuntimeError as err:
            failed.append((title, str(err)))
            print(f"[!] Échec : {title} ({err})")

    print("Résumé final")
    print(f"- Total tâches Gantt: {len(gantt_tasks)}")
    print(f"- Déjà présentes (issues): {already_present}")
    print(f"- Issues créées: {len(created_issues)}")
    print(f"- Issues déjà présentes dans le project: {already_in_project}")
    print(f"- Titres de phase ajoutés au project: {len(phase_markers)}")
    print(f"- Échouées: {len(failed)}")
    print("- Issues ajoutées:")
    if created_issues:
        for title in created_issues:
            print(f"  * {title}")
    else:
        print("  * (aucun)")

    if phase_markers:
        print("- Repères de phase créés:")
        for title in phase_markers:
            print(f"  * {title}")

    if failed:
        print("- Détails des échecs:")
        for title, err in failed:
            print(f"  * {title}: {err}")
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        raise SystemExit(2)
