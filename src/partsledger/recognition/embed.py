"""DINOv2-ViT-S/14 embedding primitive — TASK-039 (IDEA-007 Stage 1).

Loads the ``facebookresearch/dinov2`` ViT-S/14 backbone via ``torch.hub``
once, caches it process-wide, and turns a BGR ``np.ndarray`` into a 768-D
L2-normalised ``float32`` vector. The backbone stays frozen — ``eval()``
only, no fine-tuning.

Design — portability + testability:

- ``torch`` / ``cv2`` are imported lazily inside the functions that need
  them, so ``import partsledger.recognition.embed`` is cheap on a host
  without the heavy stack (matches :mod:`partsledger.capture.viewfinder`).
- The heavy forward pass is injected: :func:`embed` accepts ``model`` and
  ``preprocess`` seams, and :func:`load_model` accepts a ``loader`` seam.
  Unit tests drive the pure post-processing (shape, dtype, L2 norm,
  determinism) with a fake model and never touch ``torch`` or the network.
- The real first invocation pulls ~80 MB of weights from PyTorch Hub into
  ``~/.cache/torch/hub/``. The fully-offline pre-pull workflow is owned by
  IDEA-010 and is out of scope here.

:data:`MODEL_HASH` is a module attribute (lazily computed on first model
load) formatted ``dinov2_vits14#sha256:<hex>``. :mod:`partsledger.recognition.cache`
pins it in the cache ``meta`` table for the rebuild-on-mismatch policy.
"""

from __future__ import annotations

import hashlib
from typing import Any, Callable

# Note: ``MODEL_HASH`` is deliberately absent from ``__all__`` — it is a
# lazily computed module attribute served by ``__getattr__`` (PEP 562), not
# a static binding, so it cannot appear here without tripping pyflakes F822.
# Access it as ``embed.MODEL_HASH`` or via :func:`model_hash`.
__all__ = [
    "BACKBONE",
    "EMBED_DIM",
    "embed",
    "load_model",
    "model_hash",
    "compute_model_hash",
]

#: torch.hub repo + entrypoint for the chosen backbone (IDEA-007 closed-Q
#: *Backbone choice*). Do not parameterise — the cache schema pins 768-D.
BACKBONE = "dinov2_vits14"
_HUB_REPO = "facebookresearch/dinov2"

#: Output dimensionality of ViT-S/14. Fixed by the backbone, not configurable.
EMBED_DIM = 768

# Process-wide caches. Populated lazily by load_model(); a second import is
# zero-cost because the module object (and therefore these globals) is cached
# by the import system.
_MODEL: Any | None = None
_MODEL_HASH: str | None = None


# ---------------------------------------------------------------------------
# Model loading


def _torch_hub_load() -> Any:  # pragma: no cover - network + heavy deps
    """Pull ViT-S/14 from torch.hub, move to CPU, freeze in eval mode."""
    import torch  # local import keeps module import cheap

    model = torch.hub.load(_HUB_REPO, BACKBONE)
    model.eval()
    for param in model.parameters():
        param.requires_grad_(False)
    return model


def load_model(*, loader: Callable[[], Any] | None = None) -> Any:
    """Return the cached backbone, loading it once on first call.

    Idempotent: repeated calls (and repeated imports of this module) do
    not re-download or re-instantiate the backbone. ``loader`` is injected
    so tests can assert single-load without touching torch.
    """
    global _MODEL, _MODEL_HASH
    if _MODEL is None:
        _MODEL = (loader or _torch_hub_load)()
        _MODEL_HASH = compute_model_hash(_MODEL)
    return _MODEL


def _tensor_bytes(tensor: Any) -> bytes:
    """Canonical little-endian bytes for a torch tensor or numpy array.

    Kept torch-free so :func:`compute_model_hash` can be exercised with a
    fake state-dict of numpy arrays in the host tests.
    """
    # torch.Tensor → detach to CPU numpy; numpy arrays pass straight through.
    detach = getattr(tensor, "detach", None)
    if detach is not None:
        tensor = detach()
        cpu = getattr(tensor, "cpu", None)
        if cpu is not None:
            tensor = cpu()
        numpy = getattr(tensor, "numpy", None)
        if numpy is not None:
            tensor = numpy()
    return bytes(memoryview(tensor.tobytes()))


def compute_model_hash(model: Any) -> str:
    """Content hash over the backbone's sorted ``state_dict``.

    Returns ``dinov2_vits14#sha256:<hex>``. Stable for byte-identical
    weights, and changes if the backbone is swapped — exactly what the
    cache's rebuild-on-mismatch gate needs.
    """
    digest = hashlib.sha256()
    state = model.state_dict()
    for key in sorted(state):
        digest.update(key.encode("utf-8"))
        digest.update(_tensor_bytes(state[key]))
    return f"{BACKBONE}#sha256:{digest.hexdigest()}"


def model_hash() -> str:
    """Return :data:`MODEL_HASH`, loading the backbone if needed."""
    if _MODEL_HASH is None:
        load_model()
    assert _MODEL_HASH is not None
    return _MODEL_HASH


def __getattr__(name: str) -> Any:  # PEP 562 — lazy module-level constant
    """Expose ``embed.MODEL_HASH`` as a constant that loads on first access.

    Accessing the attribute triggers a real backbone load (network +
    torch); callers that must stay offline use :func:`compute_model_hash`
    on an injected model instead.
    """
    if name == "MODEL_HASH":
        return model_hash()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# ---------------------------------------------------------------------------
# Embedding


def _default_preprocess(image: Any) -> Any:  # pragma: no cover - heavy deps
    """BGR ``np.ndarray`` → normalised CHW float tensor batch for DINOv2.

    ViT-S/14 wants side lengths that are multiples of 14; 224 is the
    canonical short side. ImageNet mean/std normalisation matches the
    backbone's training transform.
    """
    import cv2
    import numpy as np
    import torch

    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    resized = cv2.resize(rgb, (224, 224), interpolation=cv2.INTER_AREA)
    arr = resized.astype("float32") / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype="float32")
    std = np.array([0.229, 0.224, 0.225], dtype="float32")
    arr = (arr - mean) / std
    chw = np.transpose(arr, (2, 0, 1))
    return torch.from_numpy(chw).unsqueeze(0)


def _postprocess(raw: Any) -> Any:
    """Flatten a raw feature blob to a 768-D L2-normalised float32 vector.

    Pure numpy — the unit-test seam. Raises on a zero vector (degenerate
    forward pass) rather than emitting NaNs.
    """
    import numpy as np

    vec = np.asarray(raw, dtype=np.float32).reshape(-1)
    if vec.shape[0] != EMBED_DIM:
        raise ValueError(
            f"expected a {EMBED_DIM}-D feature, got {vec.shape[0]}-D"
        )
    norm = float(np.linalg.norm(vec))
    if norm == 0.0:
        raise ValueError("cannot L2-normalise a zero feature vector")
    return (vec / norm).astype(np.float32)


def _run_model(model: Any, tensor: Any) -> Any:  # pragma: no cover - heavy
    """Forward pass under ``torch.no_grad`` when torch is present."""
    try:
        import torch
    except ImportError:  # injected fake model in tests
        return model(tensor)
    with torch.no_grad():
        return model(tensor)


def embed(
    image: Any,
    *,
    model: Any | None = None,
    preprocess: Callable[[Any], Any] | None = None,
) -> Any:
    """Embed a BGR ``np.ndarray`` into a 768-D L2-normalised float32 vector.

    ``model`` and ``preprocess`` are injected seams; by default the cached
    DINOv2 backbone and the ImageNet preprocess are used. Deterministic for
    byte-identical input (frozen eval-mode backbone, no_grad, CPU).
    """
    mdl = load_model() if model is None else model
    pre = preprocess if preprocess is not None else _default_preprocess
    features = _run_model(mdl, pre(image))
    return _postprocess(features)
