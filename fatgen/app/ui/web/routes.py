"""Flask routes for FATGen web UI."""
from __future__ import annotations
import json
import os
import uuid
from datetime import date
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, send_file, flash, jsonify
)
import io

from ...models.project import Project, PLCPlatform
from ...models.tag import Tag, IOType, SignalType, SqrtLoc
from ...models.test_config import TestCase, TestType
from ...importers.s7_csv import S7CSVImporter
from ...renderer.docx_renderer import DocxRenderer

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("FATGEN_SECRET", "fatgen-dev-secret-change-in-prod")

# In-memory project store (one project per session for Phase 1)
_PROJECTS: dict[str, dict] = {}


def _get_project() -> Project:
    pid = session.get("project_id")
    if pid and pid in _PROJECTS:
        return Project.from_dict(_PROJECTS[pid])
    return Project()


def _save_project(project: Project):
    pid = session.get("project_id")
    if not pid:
        pid = str(uuid.uuid4())
        session["project_id"] = pid
    _PROJECTS[pid] = project.to_dict()


def _get_test_cases() -> list[TestCase]:
    pid = session.get("project_id")
    key = f"{pid}_tests"
    raw = _PROJECTS.get(key, [])
    return [TestCase.from_dict(d) for d in raw]


def _save_test_cases(test_cases: list[TestCase]):
    pid = session.get("project_id")
    key = f"{pid}_tests"
    _PROJECTS[key] = [tc.to_dict() for tc in test_cases]


def _assign_doc_numbers(test_cases: list[TestCase], project: Project) -> list[TestCase]:
    for i, tc in enumerate(test_cases):
        tc.doc_number = f"DOC-FAT-{project.project_number}-{i+1:03d}"
    return test_cases


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return redirect(url_for("project_setup"))


@app.route("/project", methods=["GET", "POST"])
def project_setup():
    project = _get_project()
    if request.method == "POST":
        project.project_number = request.form.get("project_number", "")
        project.project_name   = request.form.get("project_name", "")
        project.client_name    = request.form.get("client_name", "")
        project.client_site    = request.form.get("client_site", "")
        project.si_company     = request.form.get("si_company", "")
        project.engineer       = request.form.get("engineer", "")
        project.revision       = request.form.get("revision", "A")
        project.revision_date  = request.form.get("revision_date", date.today().isoformat())
        project.plc_model      = request.form.get("plc_model", "")
        platform_str           = request.form.get("platform", "SIEMENS_S7_1500")
        try:
            project.platform = PLCPlatform[platform_str]
        except KeyError:
            project.platform = PLCPlatform.SIEMENS_S7_1500
        _save_project(project)
        flash("Project saved.", "success")
        return redirect(url_for("import_tags"))
    return render_template("project.html",
                           project=project,
                           platforms=list(PLCPlatform),
                           active_tab="project")


@app.route("/import", methods=["GET", "POST"])
def import_tags():
    project = _get_project()
    if request.method == "POST":
        f = request.files.get("csv_file")
        if f and f.filename:
            text = f.read().decode("utf-8-sig")
            importer = S7CSVImporter()
            tags = importer.parse_text(text)
            project.tags = tags
            _save_project(project)
            flash(f"Imported {len(tags)} tags.", "success")
        else:
            flash("No file selected.", "error")
        return redirect(url_for("import_tags"))

    return render_template("import.html",
                           project=project,
                           io_types=IOType,
                           active_tab="import")


@app.route("/import/tag/<tag_name>", methods=["GET", "POST"])
def edit_tag(tag_name: str):
    project = _get_project()
    tag = next((t for t in project.tags if t.name == tag_name), None)
    if tag is None:
        flash("Tag not found.", "error")
        return redirect(url_for("import_tags"))

    if request.method == "POST":
        tag.description     = request.form.get("description", tag.description)
        tag.instrument_model = request.form.get("instrument_model", "")
        tag.span_low        = float(request.form.get("span_low", 0))
        tag.span_high       = float(request.form.get("span_high", 100))
        tag.eng_units       = request.form.get("eng_units", "")
        tag.dp_range_high   = float(request.form.get("dp_range_high", 100))
        tag.dp_units        = request.form.get("dp_units", "in H2O")
        sqrt_str            = request.form.get("sqrt_extraction", "NONE")
        tag.sqrt_extraction = SqrtLoc[sqrt_str]
        tag.notes           = request.form.get("notes", "")
        _save_project(project)
        flash(f"Tag {tag_name} updated.", "success")
        return redirect(url_for("import_tags"))

    return render_template("edit_tag.html",
                           tag=tag,
                           sqrt_options=list(SqrtLoc),
                           active_tab="import")


@app.route("/tests", methods=["GET", "POST"])
def test_config():
    project = _get_project()
    test_cases = _get_test_cases()

    if request.method == "POST":
        action = request.form.get("action")

        if action == "add":
            tag_name  = request.form.get("tag_name", "")
            type_str  = request.form.get("test_type", "AI_SCALING")
            new_tc = TestCase(
                test_id=f"TC-{len(test_cases)+1:03d}",
                tag_name=tag_name,
                test_type=TestType[type_str],
                include_alarms=bool(request.form.get("include_alarms")),
                include_adc_counts=bool(request.form.get("include_adc_counts")),
                witness_blocks=int(request.form.get("witness_blocks", 2)),
                notes=request.form.get("notes", ""),
            )
            test_cases.append(new_tc)
            _save_test_cases(test_cases)
            flash("Test case added.", "success")

        elif action == "remove":
            idx = int(request.form.get("index", -1))
            if 0 <= idx < len(test_cases):
                removed = test_cases.pop(idx)
                _save_test_cases(test_cases)
                flash(f"Removed {removed.test_id}.", "success")

        elif action == "move_up":
            idx = int(request.form.get("index", -1))
            if idx > 0:
                test_cases[idx - 1], test_cases[idx] = test_cases[idx], test_cases[idx - 1]
                _save_test_cases(test_cases)

        elif action == "move_down":
            idx = int(request.form.get("index", -1))
            if idx < len(test_cases) - 1:
                test_cases[idx], test_cases[idx + 1] = test_cases[idx + 1], test_cases[idx]
                _save_test_cases(test_cases)

        return redirect(url_for("test_config"))

    tag_options = [(t.name, t.description, t.io_type.value) for t in project.tags]
    return render_template("tests.html",
                           project=project,
                           test_cases=test_cases,
                           tag_options=tag_options,
                           test_types=list(TestType),
                           active_tab="tests")


@app.route("/generate", methods=["GET", "POST"])
def generate():
    project = _get_project()
    test_cases = _get_test_cases()

    if request.method == "POST":
        action = request.form.get("action", "all")
        test_cases = _assign_doc_numbers(test_cases, project)
        _save_test_cases(test_cases)

        renderer = DocxRenderer()
        tag_map = {t.name: t for t in project.tags}

        if action == "single":
            idx = int(request.form.get("index", 0))
            if idx < 0 or idx >= len(test_cases):
                flash("Invalid test case index.", "error")
                return redirect(url_for("generate"))
            tc = test_cases[idx]
            tag = tag_map.get(tc.tag_name)
            if tag is None:
                flash(f"Tag '{tc.tag_name}' not found in project.", "error")
                return redirect(url_for("generate"))
            docx_bytes = renderer.render_single(tc, tag, project)
            filename = f"{tc.doc_number}.docx"
        else:
            valid = [tc for tc in test_cases if tc.tag_name in tag_map]
            if not valid:
                flash("No valid test cases to generate.", "error")
                return redirect(url_for("generate"))
            docx_bytes = renderer.render_all(valid, project)
            filename = f"FAT_{project.project_number}_complete.docx"

        return send_file(
            io.BytesIO(docx_bytes),
            as_attachment=True,
            download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    return render_template("generate.html",
                           project=project,
                           test_cases=test_cases,
                           active_tab="generate")


@app.route("/project/export")
def export_project():
    project = _get_project()
    test_cases = _get_test_cases()
    data = {
        "project": project.to_dict(),
        "test_cases": [tc.to_dict() for tc in test_cases],
    }
    buf = io.BytesIO(json.dumps(data, indent=2).encode())
    filename = f"{project.project_number or 'project'}.fatgen"
    return send_file(buf, as_attachment=True, download_name=filename,
                     mimetype="application/json")


@app.route("/project/import-file", methods=["POST"])
def import_project_file():
    f = request.files.get("fatgen_file")
    if not f:
        flash("No file selected.", "error")
        return redirect(url_for("project_setup"))
    try:
        data = json.loads(f.read().decode())
        project = Project.from_dict(data["project"])
        test_cases = [TestCase.from_dict(d) for d in data.get("test_cases", [])]
        _save_project(project)
        _save_test_cases(test_cases)
        flash(f"Loaded project {project.project_number}.", "success")
    except Exception as e:
        flash(f"Failed to load project: {e}", "error")
    return redirect(url_for("project_setup"))
