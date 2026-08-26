"""SSE 问答契约：帧序、结束标记和出处路径隐私。"""

from __future__ import annotations

import json
import re


def _data_events(body: str) -> list[str]:
    events: list[str] = []
    for block in body.replace("\r\n", "\n").split("\n\n"):
        data_lines = [line[5:].lstrip() for line in block.splitlines() if line.startswith("data:")]
        if data_lines:
            events.append("\n".join(data_lines))
    return events


def _is_absolute_path(value: str) -> bool:
    return bool(re.match(r"^[A-Za-z]:[\\/]", value)) or value.startswith(("/", "\\\\"))


class TestQaStreamContract:
    def test_metadata_deltas_done_and_safe_sources(self, test_client):
        response = test_client.post(
            "/api/v1/qa/stream",
            json={
                "question": "什么是死锁",
                "course": "os",
                "use_vector": False,
                "use_llm": False,
            },
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")

        events = _data_events(response.text)
        assert len(events) >= 2
        assert events.count("[DONE]") == 1
        assert events[-1] == "[DONE]"

        metadata = json.loads(events[0])
        assert isinstance(metadata.get("mode"), str)
        assert isinstance(metadata.get("sources"), list)
        assert metadata["sources"], "已标注问题应返回安全出处"

        for source in metadata["sources"]:
            file_path = source["file"]
            assert file_path.startswith("knowledge/")
            assert file_path.endswith(".md")
            assert not _is_absolute_path(file_path)
            assert ".." not in file_path.replace("\\", "/").split("/")

        for event in events[1:-1]:
            delta = json.loads(event)
            assert set(delta) == {"delta"}
            assert isinstance(delta["delta"], str)
