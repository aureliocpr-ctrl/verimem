"""AutoMemory — memoria automatica OPT-IN, sempre attraverso il gate.

Roadmap #10. La differenza di posizione rispetto a mem0/Zep: loro assorbono
ogni scambio che vedono; qui l'automatismo (a) è opt-in per costruzione — è
una classe separata: se l'app non la istanzia, non esiste; (b) non ha un
canale privilegiato — il flush passa la STESSA pipeline dell'ingest
esplicito: estrazione atomica → consolidate (droppa chit-chat) → gate
anti-confab → provenienza conversazionale → redazione segreti. Un fatto
auto-osservato nasce ``model_claim`` come tutti gli altri.

v0 deterministica e sincrona: si accumulano i turni con ``observe()`` e il
flush parte alla soglia ``max_buffer_turns`` (o manualmente / a fine
sessione con ``flush()``). Il filtro qualità NON è una seconda decisione
LLM (zero costi extra): è la pipeline stessa — il consolidate scarta il
non-durabile e il gate quarantena il non-supportato. ``min_turns`` evita il
rumore delle micro-conversazioni. Niente thread: decide il chiamante quando
osservare; un'integrazione streaming può chiamare ``observe`` per turno.
"""
from __future__ import annotations

import itertools
from typing import Any

__all__ = ["AutoMemory"]


class AutoMemory:
    """Osserva i turni di una conversazione e li ingerisce, gated, a soglia.

    Args:
        memory: un ``verimem.client.Memory`` costruito con l'``llm`` di
            estrazione (lo stesso richiesto da ``Memory.add(messages)``).
        conversation_id: prefisso di provenienza; ogni flush è numerato
            (``<id>#3``) così il TrustReport distingue le finestre.
        min_turns: sotto questa soglia un ``flush()`` è un no-op — due
            battute non sono memoria, solo rumore.
        max_buffer_turns: al raggiungimento, ``observe`` flusha da solo.
        user_name / topic: inoltrati all'ingest gated.
    """

    def __init__(self, memory: Any, *, conversation_id: str = "auto",
                 min_turns: int = 3, max_buffer_turns: int = 12,
                 user_name: str | None = None,
                 topic: str = "conversational/auto") -> None:
        if memory.llm is None:
            raise ValueError(
                "AutoMemory needs a Memory built with an extraction llm "
                "(Memory(..., llm=...)) — same requirement as add(messages)")
        self.memory = memory
        self.conversation_id = conversation_id
        self.min_turns = max(1, int(min_turns))
        self.max_buffer_turns = max(self.min_turns, int(max_buffer_turns))
        self.user_name = user_name
        self.topic = topic
        self._buffer: list[dict[str, str]] = []
        self._flush_seq = itertools.count(1)

    @property
    def pending_turns(self) -> int:
        """Turni osservati non ancora ingeriti."""
        return len(self._buffer)

    def observe(self, role: str, content: str) -> dict[str, Any]:
        """Registra un turno; flusha da solo alla soglia. Ritorna
        ``{flushed, stored, rejected, pending}`` per osservabilità."""
        text = (content or "").strip()
        if text:
            self._buffer.append({"role": str(role or "user"), "content": text})
        if len(self._buffer) >= self.max_buffer_turns:
            return self._do_flush()
        return {"flushed": False, "stored": 0, "rejected": 0,
                "pending": len(self._buffer)}

    def flush(self) -> dict[str, Any]:
        """Ingest esplicito del buffer corrente (fine sessione / topic shift).
        No-op sotto ``min_turns`` — dichiarato, non silenzioso: il ritorno
        dice ``flushed=False`` col conteggio pending."""
        if len(self._buffer) < self.min_turns:
            return {"flushed": False, "stored": 0, "rejected": 0,
                    "pending": len(self._buffer)}
        return self._do_flush()

    def _do_flush(self) -> dict[str, Any]:
        window, self._buffer = self._buffer, []
        res = self.memory.add(
            window,
            topic=self.topic,
            conversation_id=f"{self.conversation_id}#{next(self._flush_seq)}",
            user_name=self.user_name,
        )
        return {"flushed": True, "stored": int(res.get("stored", 0)),
                "rejected": int(res.get("rejected", 0)), "pending": 0,
                "ingest": res}
