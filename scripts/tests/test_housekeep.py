"""Unit tests for housekeep.py — use a scratch tasks directory."""

import io
import pathlib
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import housekeep as hk
import task_system_config as tsc


def _write(path: pathlib.Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")


class TestDeriveEpicStatus(unittest.TestCase):

    def _t(self, epic, status):
        return {"epic": epic, "status": status}

    def test_no_tasks_returns_none(self):
        self.assertIsNone(hk.derive_epic_status("foo", []))

    def test_all_closed_is_closed(self):
        tasks = [self._t("foo", "closed"), self._t("foo", "closed")]
        self.assertEqual(hk.derive_epic_status("foo", tasks), "closed")

    def test_any_active_is_active(self):
        tasks = [self._t("foo", "closed"), self._t("foo", "active"),
                 self._t("foo", "open")]
        self.assertEqual(hk.derive_epic_status("foo", tasks), "active")

    def test_open_and_closed_is_open(self):
        tasks = [self._t("foo", "closed"), self._t("foo", "open")]
        self.assertEqual(hk.derive_epic_status("foo", tasks), "open")

    def test_ignores_other_epics(self):
        tasks = [self._t("bar", "active"), self._t("foo", "closed")]
        self.assertEqual(hk.derive_epic_status("foo", tasks), "closed")


class TestPlanBuilding(unittest.TestCase):

    def _make_task(self, tmp: pathlib.Path, folder: str, task_id: str,
                   status: str, epic: str = "") -> None:
        lines = [
            "---",
            f"id: TASK-{task_id}",
            "title: sample",
            f"status: {status}",
        ]
        if epic:
            lines.append(f"epic: {epic}")
        lines += ["---", ""]
        path = tmp / folder / f"task-{task_id}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8")

    def test_no_moves_when_folders_match_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = pathlib.Path(tmp)
            self._make_task(t, "open", "001", "open")
            self._make_task(t, "closed", "002", "closed")
            plan = hk.build_plan(t)
            self.assertEqual(plan.moves, [])

    def test_open_folder_with_closed_status_plans_move(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = pathlib.Path(tmp)
            self._make_task(t, "open", "003", "closed")
            plan = hk.build_plan(t)
            self.assertEqual(len(plan.moves), 1)
            self.assertEqual(plan.moves[0].dst,
                             t / "closed" / "task-003.md")

    def test_open_folder_with_active_status_plans_move(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = pathlib.Path(tmp)
            self._make_task(t, "open", "004", "active")
            plan = hk.build_plan(t)
            self.assertEqual(len(plan.moves), 1)
            self.assertEqual(plan.moves[0].dst,
                             t / "active" / "task-004.md")

    def test_epic_follows_task_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = pathlib.Path(tmp)
            (t / "open").mkdir(parents=True, exist_ok=True)
            (t / "open" / "epic-foo.md").write_text(
                "---\nid: EPIC-001\nepic: foo\nstatus: open\n---\n",
                encoding="utf-8",
            )
            self._make_task(t, "closed", "010", "closed", epic="foo")
            self._make_task(t, "closed", "011", "closed", epic="foo")
            plan = hk.build_plan(t)
            # Epic should be moved from open/ to closed/ because all its tasks are closed.
            epic_moves = [m for m in plan.moves if "EPIC-001" in m.reason]
            self.assertEqual(len(epic_moves), 1)
            self.assertEqual(epic_moves[0].dst, t / "closed" / "epic-foo.md")


class TestDryRun(unittest.TestCase):

    def test_print_plan_with_no_changes(self):
        plan = hk.Plan()
        plan.regen = False
        buf = io.StringIO()
        hk.print_plan(plan, stream=buf)
        self.assertIn("nothing to do", buf.getvalue())

    def test_print_plan_lists_moves(self):
        plan = hk.Plan()
        plan.moves.append(hk.Move(
            src=pathlib.Path("open/task-001.md"),
            dst=pathlib.Path("closed/task-001.md"),
            reason="TASK-001 status=closed",
        ))
        plan.regen = True
        buf = io.StringIO()
        hk.print_plan(plan, stream=buf)
        out = buf.getvalue()
        self.assertIn("1 file move(s) planned", out)
        self.assertIn("open/task-001.md", out)
        self.assertIn("will be regenerated", out)


class TestInit(unittest.TestCase):

    def test_init_creates_structure_in_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = pathlib.Path(tmp)
            cfg = {
                "tasks": {"enabled": True, "base_folder": str(t / "tasks"),
                          "active": {"enabled": True},
                          "epics": {"enabled": True},
                          "releases": {"enabled": True}},
                "ideas": {"enabled": True, "base_folder": str(t / "ideas")},
                "visualizations": {"kanban": {"enabled": True}},
            }
            with redirect_stdout(io.StringIO()):
                hk.run_init(cfg)
            for sub in ("open", "active", "closed", "archive"):
                self.assertTrue((t / "tasks" / sub).is_dir(),
                                f"missing tasks/{sub}")
            self.assertTrue((t / "ideas" / "open").is_dir())
            self.assertTrue((t / "ideas" / "archived").is_dir())
            self.assertTrue((t / "tasks" / "OVERVIEW.md").exists())
            self.assertTrue((t / "tasks" / "EPICS.md").exists())
            self.assertTrue((t / "tasks" / "KANBAN.md").exists())

    def test_init_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = pathlib.Path(tmp)
            cfg = {
                "tasks": {"enabled": True, "base_folder": str(t / "tasks"),
                          "active": {"enabled": True},
                          "epics": {"enabled": True},
                          "releases": {"enabled": True}},
                "ideas": {"enabled": True, "base_folder": str(t / "ideas")},
                "visualizations": {"kanban": {"enabled": True}},
            }
            with redirect_stdout(io.StringIO()):
                hk.run_init(cfg)
            (t / "tasks" / "OVERVIEW.md").write_text("CUSTOM", encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                hk.run_init(cfg)
            self.assertEqual(
                (t / "tasks" / "OVERVIEW.md").read_text(encoding="utf-8"),
                "CUSTOM",
            )

    def test_init_respects_disabled_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = pathlib.Path(tmp)
            cfg = {
                "tasks": {"enabled": True, "base_folder": str(t / "tasks"),
                          "active": {"enabled": False},
                          "epics": {"enabled": False},
                          "releases": {"enabled": False}},
                "ideas": {"enabled": False, "base_folder": str(t / "ideas")},
                "visualizations": {"kanban": {"enabled": True}},
            }
            with redirect_stdout(io.StringIO()):
                hk.run_init(cfg)
            self.assertFalse((t / "tasks" / "active").exists())
            self.assertFalse((t / "tasks" / "archive").exists())
            self.assertFalse((t / "tasks" / "EPICS.md").exists())
            self.assertFalse((t / "ideas").exists())


class TestGenerateEpicsMd(unittest.TestCase):

    def _make_task(self, tmp: pathlib.Path, folder: str, task_id: str,
                   status: str, epic: str = "", prereqs: str = "",
                   order: int = 1) -> None:
        lines = ["---", f"id: TASK-{task_id}", "title: Task " + task_id,
                 f"status: {status}", f"order: {order}"]
        if epic:
            lines.append(f"epic: {epic}")
        if prereqs:
            lines.append(f"prerequisites: {prereqs}")
        lines += ["---", ""]
        path = tmp / folder / f"task-{task_id}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8")

    def _make_epic(self, tmp: pathlib.Path, folder: str,
                   epic_id: str, epic_name: str, title: str) -> None:
        path = tmp / folder / f"epic-{epic_name}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"---\nid: {epic_id}\nepic: {epic_name}\ntitle: {title}\nstatus: open\n---\n",
            encoding="utf-8",
        )

    def _run(self, tmp: pathlib.Path, cfg: dict | None = None) -> str:
        hk.generate_epics_md(
            tasks_dir=tmp,
            status_folders=("open", "active", "closed"),
            cfg=cfg or {"visualizations": {"epics": {"enabled": True,
                                                      "style": "dependency-graph"}}},
        )
        return (tmp / "EPICS.md").read_text(encoding="utf-8")

    def test_no_epics_writes_placeholder(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = pathlib.Path(tmp)
            content = self._run(t)
            self.assertIn("No epics defined", content)

    def test_epic_with_prereqs_produces_graph_edges(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = pathlib.Path(tmp)
            self._make_task(t, "open", "001", "open", epic="foo", order=1)
            self._make_task(t, "open", "002", "open", epic="foo",
                            prereqs="[TASK-001]", order=2)
            self._make_epic(t, "open", "EPIC-001", "foo", "Foo Epic")
            content = self._run(t)
            self.assertIn("graph TD", content)
            self.assertIn("TASK_001 --> TASK_002", content)

    def test_epic_without_prereqs_produces_flat_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = pathlib.Path(tmp)
            self._make_task(t, "open", "003", "open", epic="bar", order=1)
            self._make_task(t, "open", "004", "open", epic="bar", order=2)
            self._make_epic(t, "open", "EPIC-002", "bar", "Bar Epic")
            content = self._run(t)
            self.assertNotIn("graph TD", content)
            self.assertIn("TASK-003", content)
            self.assertIn("TASK-004", content)

    def test_gantt_style_produces_gantt_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = pathlib.Path(tmp)
            self._make_task(t, "open", "005", "open", epic="baz", order=1)
            self._make_epic(t, "open", "EPIC-003", "baz", "Baz Epic")
            cfg = {"visualizations": {"epics": {"enabled": True, "style": "gantt"}}}
            content = self._run(t, cfg)
            self.assertIn("gantt", content)
            self.assertNotIn("graph TD", content)

    def test_disabled_via_config_skips_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = pathlib.Path(tmp)
            self._make_task(t, "open", "006", "open", epic="qux", order=1)
            cfg = {"visualizations": {"epics": {"enabled": False}}}
            hk.generate_epics_md(tasks_dir=t,
                                  status_folders=("open", "active", "closed"),
                                  cfg=cfg)
            self.assertFalse((t / "EPICS.md").exists())

    def test_sections_in_index_order_not_alphabetical(self):
        # Two epics with non-alphabetical ids: EPIC-002 named "zebra"
        # comes BEFORE EPIC-010 named "alpha" in the index, so the
        # per-epic sections must follow that same numerical order.
        with tempfile.TemporaryDirectory() as tmp:
            t = pathlib.Path(tmp)
            self._make_task(t, "open", "100", "open", epic="zebra", order=1)
            self._make_task(t, "open", "101", "open", epic="alpha", order=1)
            self._make_epic(t, "open", "EPIC-002", "zebra", "Zebra Epic")
            self._make_epic(t, "open", "EPIC-010", "alpha", "Alpha Epic")
            content = self._run(t)
            i_zebra = content.find("## EPIC-002: Zebra Epic")
            i_alpha = content.find("## EPIC-010: Alpha Epic")
            self.assertNotEqual(i_zebra, -1)
            self.assertNotEqual(i_alpha, -1)
            self.assertLess(
                i_zebra, i_alpha,
                "Per-epic sections must follow index order (EPIC-002 before EPIC-010), "
                "not alphabetical (alpha before zebra).",
            )

    def test_each_epic_section_has_back_to_top_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = pathlib.Path(tmp)
            self._make_task(t, "open", "200", "open", epic="alpha", order=1)
            self._make_task(t, "open", "201", "open", epic="beta", order=1)
            self._make_epic(t, "open", "EPIC-001", "alpha", "Alpha Epic")
            self._make_epic(t, "open", "EPIC-002", "beta", "Beta Epic")
            content = self._run(t)

            # Each section heading must be followed (within a few lines)
            # by a back-to-top link pointing at #index.
            for heading in ("## EPIC-001: Alpha Epic", "## EPIC-002: Beta Epic"):
                i = content.find(heading)
                self.assertNotEqual(i, -1, f"missing heading {heading!r}")
                tail = content[i: i + 200]
                self.assertIn("[↑ back to top](#index)", tail,
                              f"no back-to-top link near {heading!r}")

    def test_unassigned_section_has_back_to_top_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = pathlib.Path(tmp)
            # Need at least one epic-bound task for the Unassigned branch
            # to render — the renderer skips the per-epic + Unassigned
            # block entirely when by_epic is empty.
            self._make_task(t, "open", "300", "open", order=1)  # no epic
            self._make_task(t, "open", "301", "open", epic="alpha", order=1)
            self._make_epic(t, "open", "EPIC-001", "alpha", "Alpha")
            content = self._run(t)
            i = content.find("## Unassigned")
            self.assertNotEqual(i, -1, content)
            tail = content[i: i + 200]
            self.assertIn("[↑ back to top](#index)", tail)


class TestGenerateKanbanMd(unittest.TestCase):

    def _make_task(self, tmp: pathlib.Path, folder: str, task_id: str,
                   status: str, assigned: str = "", title: str = "") -> None:
        title_value = title or f"Task {task_id}"
        lines = ["---", f"id: TASK-{task_id}", f'title: "{title_value}"',
                 f"status: {status}"]
        if assigned:
            lines.append(f"assigned: {assigned}")
        lines += ["---", ""]
        path = tmp / folder / f"task-{task_id}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8")

    def _run(self, tmp: pathlib.Path, cfg: dict | None = None) -> str:
        hk.generate_kanban_md(
            tasks_dir=tmp,
            status_folders=("open", "active", "closed"),
            cfg=cfg or {"visualizations": {"kanban": {"enabled": True}},
                        "tasks": {"active": {"enabled": True}}},
        )
        return (tmp / "KANBAN.md").read_text(encoding="utf-8")

    def test_task_appears_in_correct_column(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = pathlib.Path(tmp)
            self._make_task(t, "open", "001", "open")
            self._make_task(t, "active", "002", "active")
            self._make_task(t, "closed", "003", "closed")
            content = self._run(t)
            lines = content.splitlines()
            open_idx = next(i for i, l in enumerate(lines) if "  Open" in l)
            active_idx = next(i for i, l in enumerate(lines) if "  Active" in l)
            closed_idx = next(i for i, l in enumerate(lines) if "  Closed" in l)
            task001_idx = next(i for i, l in enumerate(lines) if "TASK-001" in l)
            task002_idx = next(i for i, l in enumerate(lines) if "TASK-002" in l)
            task003_idx = next(i for i, l in enumerate(lines) if "TASK-003" in l)
            self.assertLess(open_idx, task001_idx)
            self.assertLess(task001_idx, active_idx)
            self.assertLess(active_idx, task002_idx)
            self.assertLess(task002_idx, closed_idx)
            self.assertLess(closed_idx, task003_idx)

    def test_assigned_badge_appears(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = pathlib.Path(tmp)
            self._make_task(t, "open", "004", "open", assigned="alice")
            content = self._run(t)
            self.assertIn("@alice", content)

    def test_disabled_skips_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = pathlib.Path(tmp)
            self._make_task(t, "open", "005", "open")
            hk.generate_kanban_md(
                tasks_dir=t,
                status_folders=("open", "active", "closed"),
                cfg={"visualizations": {"kanban": {"enabled": False}},
                     "tasks": {"active": {"enabled": True}}},
            )
            self.assertFalse((t / "KANBAN.md").exists())

    def test_contains_mermaid_kanban_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = pathlib.Path(tmp)
            self._make_task(t, "open", "006", "open")
            content = self._run(t)
            self.assertIn("```mermaid", content)
            self.assertIn("kanban", content)

    def test_kanban_label_strips_backticks(self):
        # Regression for TASK-321: a leading backtick in a kanban label put
        # mermaid into markdown-string mode and broke the parser. Strip both
        # backticks and double quotes from labels.
        with tempfile.TemporaryDirectory() as tmp:
            t = pathlib.Path(tmp)
            self._make_task(t, "open", "007", "open",
                            title="`/ts-task-active` nags on `branch:`")
            content = self._run(t)
            kanban_line = next(line for line in content.splitlines()
                               if "TASK_007" in line)
            self.assertNotIn("`", kanban_line)
            self.assertIn("/ts-task-active", kanban_line)


class TestInitEndToEnd(unittest.TestCase):
    """End-to-end: simulate fresh repo install using the distribution layout."""

    def test_init_then_apply_with_a_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = pathlib.Path(tmp)
            cfg = {
                "tasks": {
                    "enabled": True,
                    "base_folder": str(t / "tasks"),
                    "active": {"enabled": True},
                    "epics": {"enabled": True},
                    "releases": {"enabled": True},
                },
                "ideas": {"enabled": True, "base_folder": str(t / "ideas")},
                "visualizations": {
                    "epics": {"enabled": True, "style": "dependency-graph"},
                    "kanban": {"enabled": True},
                },
            }
            # Step 1: --init creates the folder structure
            with redirect_stdout(io.StringIO()):
                hk.run_init(cfg)

            tasks_dir = t / "tasks"
            for sub in ("open", "active", "closed", "archive"):
                self.assertTrue((tasks_dir / sub).is_dir())
            self.assertTrue((t / "ideas" / "open").is_dir())
            self.assertTrue((t / "ideas" / "archived").is_dir())
            self.assertTrue((tasks_dir / "OVERVIEW.md").exists())
            self.assertTrue((tasks_dir / "EPICS.md").exists())
            self.assertTrue((tasks_dir / "KANBAN.md").exists())

            # Step 2: drop in a task and run plan+generate
            task_file = tasks_dir / "open" / "task-001-hello.md"
            task_file.write_text(
                "---\nid: TASK-001\ntitle: Hello\nstatus: open\n---\n",
                encoding="utf-8",
            )
            plan = hk.build_plan(tasks_dir, ("open", "active", "closed"),
                                  epics_enabled=True)
            self.assertEqual(plan.moves, [], "No moves expected — status matches folder")

            hk.generate_epics_md(tasks_dir, ("open", "active", "closed"), cfg)
            hk.generate_kanban_md(tasks_dir, ("open", "active", "closed"), cfg)

            kanban = (tasks_dir / "KANBAN.md").read_text(encoding="utf-8")
            self.assertIn("TASK-001", kanban)

            # Step 3: close the task and verify a move is planned
            task_file.write_text(
                "---\nid: TASK-001\ntitle: Hello\nstatus: closed\n---\n",
                encoding="utf-8",
            )
            plan = hk.build_plan(tasks_dir, ("open", "active", "closed"),
                                  epics_enabled=True)
            self.assertEqual(len(plan.moves), 1)
            self.assertEqual(plan.moves[0].dst,
                             tasks_dir / "closed" / "task-001-hello.md")

    def test_version_flag(self):
        import subprocess, sys
        result = subprocess.run(
            [sys.executable, str(pathlib.Path(hk.__file__)), "--version"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("housekeep", result.stdout)


class TestOrderValidator(unittest.TestCase):
    def _task(self, tid: str, *, epic, order):
        return {"id": tid, "epic": epic, "order": order,
                "_path": pathlib.Path(f"/tmp/{tid}.md")}

    def test_happy_path_passes(self):
        tasks = [
            self._task("TASK-001", epic="alpha", order=1),
            self._task("TASK-002", epic="alpha", order=2),
            self._task("TASK-003", epic="beta",  order=1),
        ]
        self.assertEqual(hk.validate_order_fields(tasks), [])

    def test_missing_order_fails(self):
        tasks = [
            self._task("TASK-001", epic="alpha", order=1),
            self._task("TASK-002", epic="alpha", order=None),
        ]
        failures = hk.validate_order_fields(tasks)
        self.assertEqual(len(failures), 1)
        self.assertIn("TASK-002", failures[0])
        self.assertIn("alpha", failures[0])

    def test_question_mark_treated_as_missing(self):
        tasks = [self._task("TASK-001", epic="alpha", order="?")]
        failures = hk.validate_order_fields(tasks)
        self.assertEqual(len(failures), 1)
        self.assertIn("missing/blank/'?'", failures[0])

    def test_duplicate_order_fails_naming_both(self):
        tasks = [
            self._task("TASK-001", epic="alpha", order=2),
            self._task("TASK-002", epic="alpha", order=2),
        ]
        failures = hk.validate_order_fields(tasks)
        self.assertEqual(len(failures), 1)
        self.assertIn("TASK-001", failures[0])
        self.assertIn("TASK-002", failures[0])

    def test_tasks_without_epic_ignored(self):
        tasks = [self._task("TASK-001", epic=None, order=None)]
        self.assertEqual(hk.validate_order_fields(tasks), [])


class TestFixOrder(unittest.TestCase):
    def test_renumbers_contiguously_per_epic(self):
        with tempfile.TemporaryDirectory() as td:
            t = pathlib.Path(td)
            f1 = t / "task-001.md"
            f2 = t / "task-002.md"
            f3 = t / "task-003.md"
            _write(f1, "---\nid: TASK-001\nepic: alpha\norder: 5\n---\n")
            _write(f2, "---\nid: TASK-002\nepic: alpha\norder: ?\n---\n")
            _write(f3, "---\nid: TASK-003\nepic: alpha\n---\n")

            tasks = [hk.parse_frontmatter(p) for p in (f1, f2, f3)]
            changes = hk.fix_order_fields(tasks)

            # All three should be rewritten — none currently match its target.
            self.assertEqual(len(changes), 3)
            after = {p.name: hk.parse_frontmatter(p)["order"]
                     for p in (f1, f2, f3)}
            self.assertEqual(set(after.values()), {"1", "2", "3"})

    def test_idempotent_on_already_clean(self):
        with tempfile.TemporaryDirectory() as td:
            t = pathlib.Path(td)
            f1 = t / "task-001.md"
            f2 = t / "task-002.md"
            _write(f1, "---\nid: TASK-001\nepic: alpha\norder: 1\n---\n")
            _write(f2, "---\nid: TASK-002\nepic: alpha\norder: 2\n---\n")

            tasks = [hk.parse_frontmatter(p) for p in (f1, f2)]
            self.assertEqual(hk.fix_order_fields(tasks), [])


class TestEffortLabels(unittest.TestCase):
    """Verify that the canonical-six and legacy effort labels round-trip
    cleanly through the frontmatter parser and renderer."""

    CANONICAL = [
        "XS (<30m)",
        "Small (<2h)",
        "Medium (2-8h)",
        "Large (8-24h)",
        "Extra Large (24-40h)",
        "XXL (>40h)",
    ]
    LEGACY = [
        "Trivial (<30m)",
        "Small (1-2h)",
        "Small (1-3h)",
        "Small (2-4h)",
        "Large (>8h)",
    ]

    def test_canonical_labels_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            t = pathlib.Path(td)
            for i, label in enumerate(self.CANONICAL, start=1):
                p = t / f"task-{i:03d}.md"
                _write(p, f"---\nid: TASK-{i:03d}\nstatus: open\neffort: {label}\n---\n")
                fm = hk.parse_frontmatter(p)
                self.assertEqual(fm["effort"], label)

    def test_legacy_labels_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            t = pathlib.Path(td)
            for i, label in enumerate(self.LEGACY, start=1):
                p = t / f"task-{i:03d}.md"
                _write(p, f"---\nid: TASK-{i:03d}\nstatus: open\neffort: {label}\n---\n")
                fm = hk.parse_frontmatter(p)
                self.assertEqual(fm["effort"], label)

    def test_effort_actual_field_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            t = pathlib.Path(td)
            p = t / "task-001.md"
            _write(p, "---\nid: TASK-001\nstatus: closed\neffort: Medium (2-8h)\neffort_actual: Large (8-24h)\n---\n")
            fm = hk.parse_frontmatter(p)
            self.assertEqual(fm["effort"], "Medium (2-8h)")
            self.assertEqual(fm["effort_actual"], "Large (8-24h)")


class TestPausedFolder(unittest.TestCase):
    """End-to-end checks that paused/ is a first-class status folder."""

    def _setup_repo(self, t: pathlib.Path) -> pathlib.Path:
        tasks_dir = t / "tasks"
        for sub in ("open", "active", "paused", "closed"):
            (tasks_dir / sub).mkdir(parents=True)
        return tasks_dir

    def test_paused_folder_is_scanned(self):
        with tempfile.TemporaryDirectory() as td:
            t = pathlib.Path(td)
            tasks_dir = self._setup_repo(t)
            f = tasks_dir / "paused" / "task-001.md"
            _write(f, "---\nid: TASK-001\ntitle: T1\nstatus: paused\n---\n")
            items = hk.scan_folder(tasks_dir, ("open", "active", "paused", "closed"))
            ids = [it.get("id") for it in items]
            self.assertIn("TASK-001", ids)

    def test_paused_to_active_planned(self):
        with tempfile.TemporaryDirectory() as td:
            t = pathlib.Path(td)
            tasks_dir = self._setup_repo(t)
            f = tasks_dir / "paused" / "task-001.md"
            _write(f, "---\nid: TASK-001\ntitle: T1\nstatus: active\n---\n")
            plan = hk.build_plan(tasks_dir, ("open", "active", "paused", "closed"),
                                  epics_enabled=False)
            self.assertEqual(len(plan.moves), 1)
            self.assertEqual(plan.moves[0].dst,
                             tasks_dir / "active" / "task-001.md")

    def test_paused_to_closed_planned(self):
        with tempfile.TemporaryDirectory() as td:
            t = pathlib.Path(td)
            tasks_dir = self._setup_repo(t)
            f = tasks_dir / "paused" / "task-001.md"
            _write(f, "---\nid: TASK-001\ntitle: T1\nstatus: closed\n---\n")
            plan = hk.build_plan(tasks_dir, ("open", "active", "paused", "closed"),
                                  epics_enabled=False)
            self.assertEqual(len(plan.moves), 1)
            self.assertEqual(plan.moves[0].dst,
                             tasks_dir / "closed" / "task-001.md")


class TestPausedConfig(unittest.TestCase):
    def test_active_disabled_forces_paused_off(self):
        cfg = {"tasks": {"active": {"enabled": False},
                         "paused": {"enabled": True}}}
        self.assertFalse(tsc.paused_enabled(cfg))

    def test_paused_disabled_collapses(self):
        cfg = {"tasks": {"active": {"enabled": True},
                         "paused": {"enabled": False}}}
        self.assertFalse(tsc.paused_enabled(cfg))

    def test_both_enabled(self):
        cfg = {"tasks": {"active": {"enabled": True},
                         "paused": {"enabled": True}}}
        self.assertTrue(tsc.paused_enabled(cfg))

    def test_status_folders_omits_paused_when_disabled(self):
        self.assertEqual(
            hk._status_folders(active_enabled=True, paused_enabled=False),
            ("open", "active", "closed"),
        )

    def test_status_folders_includes_paused_when_enabled(self):
        self.assertEqual(
            hk._status_folders(active_enabled=True, paused_enabled=True),
            ("open", "active", "paused", "closed"),
        )

    def test_status_folders_active_off_implies_paused_off(self):
        # Caller computes paused_enabled via tsc.paused_enabled, which
        # already encodes the truth-table; if active is off, paused must
        # be off too.
        self.assertEqual(
            hk._status_folders(active_enabled=False, paused_enabled=False),
            ("open", "closed"),
        )


class TestPausedSortRank(unittest.TestCase):
    def test_sort_key_orders_status_then_order(self):
        tasks = [
            {"status": "closed", "order": 1},
            {"status": "open", "order": 2},
            {"status": "active", "order": 1},
            {"status": "paused", "order": 1},
            {"status": "open", "order": 1},
        ]
        ordered = sorted(tasks, key=hk._flat_list_sort_key)
        self.assertEqual(
            [(t["status"], t["order"]) for t in ordered],
            [("open", 1), ("open", 2), ("paused", 1), ("active", 1), ("closed", 1)],
        )


class TestEpicsRendererPaused(unittest.TestCase):
    def test_per_epic_denominator_includes_paused(self):
        with tempfile.TemporaryDirectory() as td:
            t = pathlib.Path(td)
            tasks_dir = t / "tasks"
            for sub in ("open", "active", "paused", "closed"):
                (tasks_dir / sub).mkdir(parents=True)
            _write(tasks_dir / "open" / "task-001.md",
                   "---\nid: TASK-001\ntitle: T1\nstatus: open\nepic: alpha\norder: 1\n---\n")
            _write(tasks_dir / "paused" / "task-002.md",
                   "---\nid: TASK-002\ntitle: T2\nstatus: paused\nepic: alpha\norder: 2\n---\n")
            _write(tasks_dir / "closed" / "task-003.md",
                   "---\nid: TASK-003\ntitle: T3\nstatus: closed\nepic: alpha\norder: 3\n---\n")
            _write(tasks_dir / "open" / "epic-001.md",
                   "---\nid: EPIC-001\ntitle: Alpha\nstatus: open\nepic: alpha\nname: alpha\n---\n")

            hk.generate_epics_md(tasks_dir, ("open", "active", "paused", "closed"))
            content = (tasks_dir / "EPICS.md").read_text(encoding="utf-8")
            # 1 closed out of 3 (open + paused + closed) — NOT 1/2.
            self.assertIn("1/3", content)


class TestKanbanPausedLane(unittest.TestCase):
    def test_paused_lane_between_active_and_closed(self):
        with tempfile.TemporaryDirectory() as td:
            t = pathlib.Path(td)
            tasks_dir = t / "tasks"
            for sub in ("open", "active", "paused", "closed"):
                (tasks_dir / sub).mkdir(parents=True)
            _write(tasks_dir / "paused" / "task-001.md",
                   "---\nid: TASK-001\ntitle: T1\nstatus: paused\nepic: alpha\n---\n")

            hk.generate_kanban_md(tasks_dir, ("open", "active", "paused", "closed"))
            content = (tasks_dir / "KANBAN.md").read_text(encoding="utf-8")
            i_active = content.find("Active")
            i_paused = content.find("Paused")
            i_closed = content.find("Closed")
            self.assertGreater(i_paused, i_active)
            self.assertGreater(i_closed, i_paused)
            self.assertIn("TASK_001", content)


class TestMdCellEscape(unittest.TestCase):
    """Unit-tests the shared `_md_cell` escape helper."""

    def test_angle_brackets_become_entities(self):
        self.assertEqual(hk._md_cell("archive/<version>/"),
                         "archive/&lt;version&gt;/")

    def test_pipe_is_backslash_escaped(self):
        self.assertEqual(hk._md_cell("a | b"), "a \\| b")

    def test_idempotent_on_already_safe_text(self):
        self.assertEqual(hk._md_cell("plain title"), "plain title")

    def test_double_application_is_safe(self):
        once = hk._md_cell("archive/<version>/")
        twice = hk._md_cell(once)
        # Already-escaped output passes through unchanged because we only
        # escape raw `<` / `>` / `|`. The `&lt;` / `&gt;` entities have no
        # such characters.
        self.assertEqual(once, twice)


class TestGeneratedMarkdownIsLintClean(unittest.TestCase):
    """Run housekeep against a fixture tree containing markdown-hostile
    titles and assert markdownlint reports zero findings on every
    autogenerated file.

    The fixture is deliberately mean: titles contain ``<version>`` (MD033
    bait), pipe characters (table column separator), and angle-bracketed
    fragments inside an epic name (kanban heading). Without the
    `_md_cell` escape, the generated tables fail markdownlint.
    """

    def setUp(self):
        import shutil
        self.markdownlint = shutil.which("markdownlint-cli2")
        if not self.markdownlint:
            self.skipTest("markdownlint-cli2 not installed")

    def _build_fixture(self, root: pathlib.Path) -> pathlib.Path:
        tasks_dir = root / "tasks"
        for sub in ("open", "active", "paused", "closed"):
            (tasks_dir / sub).mkdir(parents=True)
        _write(tasks_dir / "open" / "epic-001.md",
               "---\nid: EPIC-001\ntitle: Alpha epic\n"
               "status: open\nepic: alpha\nname: alpha\n---\n")
        # Hostile titles: <version>, pipe, ampersand entities.
        _write(tasks_dir / "open" / "task-001.md",
               "---\nid: TASK-001\n"
               "title: Snapshot OVERVIEW into archive/<version>/ on release\n"
               "status: open\nepic: alpha\norder: 1\n"
               "effort: Small (<2h)\ncomplexity: Junior\n---\n")
        _write(tasks_dir / "open" / "task-002.md",
               "---\nid: TASK-002\n"
               "title: A | B pipe-bearing title\n"
               "status: open\nepic: alpha\norder: 2\n"
               "effort: Medium (2-8h)\ncomplexity: Medium\n---\n")
        return tasks_dir

    def _lint(self, *paths: pathlib.Path) -> tuple[int, str]:
        import subprocess
        result = subprocess.run(
            [self.markdownlint, *map(str, paths)],
            capture_output=True, text=True,
        )
        return result.returncode, result.stdout + result.stderr

    def test_epics_md_is_lint_clean_for_hostile_titles(self):
        with tempfile.TemporaryDirectory() as td:
            tasks_dir = self._build_fixture(pathlib.Path(td))
            hk.generate_epics_md(tasks_dir, ("open", "active", "paused", "closed"))
            rc, output = self._lint(tasks_dir / "EPICS.md")
            self.assertEqual(rc, 0, output)

    def test_kanban_md_is_lint_clean_for_hostile_titles(self):
        with tempfile.TemporaryDirectory() as td:
            tasks_dir = self._build_fixture(pathlib.Path(td))
            hk.generate_kanban_md(tasks_dir, ("open", "active", "paused", "closed"))
            rc, output = self._lint(tasks_dir / "KANBAN.md")
            self.assertEqual(rc, 0, output)

    def test_idempotent_regen(self):
        """Re-running generate_*_md must not change the bytes on disk."""
        with tempfile.TemporaryDirectory() as td:
            tasks_dir = self._build_fixture(pathlib.Path(td))
            hk.generate_epics_md(tasks_dir, ("open", "active", "paused", "closed"))
            hk.generate_kanban_md(tasks_dir, ("open", "active", "paused", "closed"))
            epics_first = (tasks_dir / "EPICS.md").read_bytes()
            kanban_first = (tasks_dir / "KANBAN.md").read_bytes()
            hk.generate_epics_md(tasks_dir, ("open", "active", "paused", "closed"))
            hk.generate_kanban_md(tasks_dir, ("open", "active", "paused", "closed"))
            self.assertEqual(epics_first, (tasks_dir / "EPICS.md").read_bytes())
            self.assertEqual(kanban_first, (tasks_dir / "KANBAN.md").read_bytes())


class TestSyncTaskSystem(unittest.TestCase):
    """Smoke-tests the in-repo sync script against the real package layout."""

    def setUp(self):
        repo_root = pathlib.Path(hk.__file__).resolve().parent.parent
        self.sync = repo_root / "scripts" / "sync_task_system.py"
        self.repo_root = repo_root
        if not self.sync.exists():
            self.skipTest("sync_task_system.py not present in this checkout")

    def test_check_returns_zero_when_in_sync(self):
        import subprocess, sys
        result = subprocess.run(
            [sys.executable, str(self.sync), "--check"],
            capture_output=True, text=True, cwd=self.repo_root,
        )
        self.assertEqual(
            result.returncode, 0,
            f"--check failed: {result.stdout}{result.stderr}",
        )


if __name__ == "__main__":
    unittest.main()
