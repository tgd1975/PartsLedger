"""Visual-recognition pipeline — EPIC-006 (IDEA-007).

The recognition stack turns a captured BGR still into an inventory
side-effect. It is built in dependency order:

- :mod:`partsledger.recognition.embed` — DINOv2-ViT-S/14 embedding
  primitive (TASK-039).
- :mod:`partsledger.recognition.cache` — sqlite-backed embedding store
  with cosine nearest-neighbour search (TASK-040).
- :mod:`partsledger.recognition.pipeline` — banded ``classify()`` and
  the full ``run()`` glue (TASK-041, TASK-043).
- :mod:`partsledger.recognition.vlm` — OpenAI-compatible VLM adapter
  (TASK-042).
- :mod:`partsledger.recognition.undo` — depth-1 undo journal (TASK-044).

Every module follows the project portability convention: heavy
third-party imports (``torch``, ``cv2``, ``numpy``, ``requests``,
``sqlite-vec``) are deferred to call time so the package imports cheaply
on a host with none of them installed, and the pure logic stays unit
testable behind injected seams.
"""

from __future__ import annotations
