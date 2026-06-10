# skill: motioncomic

**Quadrinho em VÍDEO com zoom** (motion comic, `../../docs/02`). A câmera dá **zoom em cada quadro
durante a sua narração**; voz via `inemavox`, balão/SFX em camada, narração é voz-off.

> **Construída (V1).** Entrada: [`SKILL.md`](SKILL.md). Pipeline: quadro textless (flux2-klein) →
> balão/SFX → narração (TTS) → `ffmpeg zoompan` (push-in) → MP4 16:9. Reusa `imgclient`/`render`/
> `artes` do `folder`. Pré-req: `inemaimg` (:8000) + daemon `inemavox` (:7860).

Demo gerada: *"A Escada Invisível de Lia"* (Pirâmide de Maslow) — 10 páginas / 50 quadros / ~4m47s.
