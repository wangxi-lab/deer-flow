from __future__ import annotations

from pathlib import Path

from deerflow.skills.loader import load_skills
from deerflow.skills.parser import parse_skill_file


def test_knowledge_base_qa_skill_parses():
    skill_file = Path("skills/public/knowledge-base-qa/SKILL.md")

    skill = parse_skill_file(skill_file, category="public", relative_path=Path("knowledge-base-qa"))

    assert skill is not None
    assert skill.name == "knowledge-base-qa"
    assert skill.category == "public"
    assert "knowledge base" in skill.description.lower()


def test_knowledge_base_qa_skill_is_discoverable():
    skills = load_skills(use_config=False)

    skill = next((item for item in skills if item.name == "knowledge-base-qa"), None)

    assert skill is not None
    assert skill.enabled is True
    assert skill.relative_path == Path("knowledge-base-qa")
