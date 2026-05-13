# Versionierung

Die Dokumentation wird mit **mike** versioniert, um verschiedene Zustände des Projekts (z.B. `latest`, `dev`, `v0.1.0`) gleichzeitig bereitzustellen.

## Deployment-Strategie

1.  **Main Branch:** Jeder Push auf `main` aktualisiert die `dev`-Version der Dokumentation.
2.  **Tags:** Jeder Tag (`v*`) erstellt eine neue permanente Version und aktualisiert den Alias `latest`.

## Manuelles Deployment

Um eine Version lokal zu bauen und auf `gh-pages` zu pushen:

```bash
mike deploy --push --update-aliases 0.1.0 latest
mike set-default --push latest
```

## Versionsauswahl

Der Versions-Switcher befindet sich in der Kopfzeile der Dokumentation. Er ermöglicht es Benutzern, schnell zwischen stabilen Releases und dem aktuellen Entwicklungsstand zu wechseln.
