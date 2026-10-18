# Rehearsal submission materials

- **[Pitch deck PDF](Rehearsal_Pitch_Deck.pdf)** — upload this as the slide presentation.
- **[Editable PowerPoint](Rehearsal_Pitch_Deck.pptx)** — 10 slides, with editable text, shapes, charts, links and speaker notes.
- **[Demo video](https://youtu.be/XCLzMpVXXHU)** — uploaded project walkthrough.
- [Video recording script](VIDEO_SCRIPT.md) — narration with screen cues.
- [Plain video narration](VIDEO_NARRATION.txt) — conversational teleprompter copy.
- [Slide overview](slide-previews/contact-sheet.png) — preview all 10 pages.

The PDF is the reference layout. Its app/repository/video links and evidence source
links are clickable. The figures are from the repository's saved live AMD flow
and provisional evaluation artifacts; no new model request was needed to build
the deck. Synthetic data, prompt tuning, label disagreement and CPU replay are
identified in the slides. No production ROI or GPU speedup is claimed.

Build from the repository root with a Python virtual environment:

```bash
python -m pip install -r submission/requirements-slides.txt
python submission/build_slides.py
```

The generator uses the same point coordinates for PDF and PowerPoint.
It expects Liberation Sans/Mono fonts under
`/usr/share/fonts/truetype/liberation/`; adapt `FONT_DIR` for another platform.
PDF fonts are embedded. The PowerPoint uses Arial for text, and Liberation Mono
for the short CSV excerpt. The embedded PDF font attribution is retained in
[FONT_NOTICES.txt](FONT_NOTICES.txt).

These materials do not constitute a completed event submission. Form fields,
final team review and the submission confirmation remain separate.
