# Changelog Workflow

Wir verwenden **Conventional Commits** und **git-cliff**, um unseren Changelog automatisch zu pflegen.

## Commit-Nachrichten Format

Nachrichten sollten folgendem Muster folgen:

```text
<typ>(<bereich>): <beschreibung>

[optionaler body]

[optionaler footer]
```

**Typen:**  
- `feat`: Eine neue Funktion  
- `fix`: Ein Bugfix  
- `docs`: Änderungen an der Dokumentation  
- `style`: Änderungen am Format/Styling (kein Code-Effekt)  
- `refactor`: Code-Änderung, die weder einen Bug fix Bürger noch ein Feature hinzufügt  
- `perf`: Leistungsverbesserungen  
- `test`: Hinzufügen oder Korrigieren von Tests  
- `chore`: Änderungen am Build-Prozess oder Hilfsmitteln  

## Automatisierung

Bei jedem Release (Push eines Tags `v*`) führt die GitHub Action `git-cliff` aus, aktualisiert die Datei `CHANGELOG.md` im Hauptverzeichnis und erstellt ein GitHub Release.
