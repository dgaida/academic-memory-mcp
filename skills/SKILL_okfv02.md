---
name: okf-email-compliance
description: "Diese Skill MUSS immer verwendet werden, wenn eine E-Mail unter Verwendung von Wissen aus einem OKF-Bundle (Open Knowledge Format v0.2, z. B. unter packages/okf erzeugte Bundles) automatisiert oder halbautomatisiert beantwortet, entworfen oder vorformuliert wird. Sie stellt sicher, dass jede Aussage im E-Mail-Entwurf gegen Vertrauensstufe (verified), Aktualität (stale_after, status) und Herkunft (sources) geprüft wurde, bevor sie verwendet wird, und dass Berechnungen ausschließlich über attestierte Attested-Computation-Konzepte laufen — niemals durch eigenes Rechnen des LLM. Trigger: Anfragen zu Prüfungsordnungen, Fristen, Terminverschiebungen, Notenberechnungen, ECTS-Regelungen oder jede andere administrative/rechtlich relevante E-Mail-Anfrage an eine Hochschule."
---

## Zweck

Diese Skill setzt die [OKF-v0.2-Spezifikation](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf) für den Anwendungsfall "automatisierte E-Mail-Beantwortung" durchsetzbar um. Sie ergänzt die bestehende Projekt-Doku unter `packages/okf/email-recommendations/` um die dort fehlenden bzw. zu lax formulierten Punkte — insbesondere die vollständige Attestierungs-Pipeline (§10.5) und die verpflichtende Kopplung von Trust-Tier- und Freshness-Prüfung.

**Grundregel:** Jede sachliche Aussage in einer generierten E-Mail, die sich auf universitäre Regeln, Fristen, Berechnungen oder Zusagen bezieht, muss auf ein konkretes OKF-Concept zurückführbar sein, das die untenstehende Prüfkette vollständig durchlaufen hat. Kein Concept, keine Aussage.

---

## 1. Retrieval: Progressive Disclosure statt Volltext-Dump

- Niemals das gesamte Bundle in den Kontext laden.
- Erst `index.md` der obersten Ebene bzw. des vermutlich relevanten Unterordners (`concepts/`, `tables/`, `entities/`, `definitions/`) lesen, um die Themenübersicht zu erhalten.
- Erst danach das konkret relevante Concept gezielt nachladen (z. B. `/concepts/exam-withdrawal-illness.md`).
- Bei Multi-Hop-Fragen (z. B. "Konzept A verweist auf Tabelle B") den Markdown-Links im Body folgen (§6.1) — bundle-relative Links (`/…`) sind die bevorzugte Form, relative Links (`./…`) sind ebenfalls gültig.
- Tote Links (Ziel existiert nicht) sind laut Spec kein Fehler, sondern können "noch nicht geschriebenes Wissen" bedeuten (§6.1) — nicht als Systemfehler behandeln, sondern als "hier gibt es (noch) keine belastbare Information" werten und das in der Antwort entsprechend vorsichtig formulieren.

## 2. Pflicht-Prüfkette pro geladenem Concept

Für **jedes** Concept, aus dem eine Aussage in die E-Mail übernommen wird, müssen alle vier Prüfungen durchlaufen werden — **in dieser Reihenfolge**, und **immer alle vier**, unabhängig davon, wie hoch die Vertrauensstufe ist:

### 2.1 Status prüfen (`status`, §5.4)

- `status: deprecated` → Concept **nicht** als aktuelle Regelung zitieren. Nur verwenden, wenn explizit nach historischem Stand gefragt wird, und dann klar als veraltet kennzeichnen.
- `status: draft` → Nicht als finale Auskunft verwenden. In der Antwort ggf. darauf hinweisen, dass die Regelung noch nicht final ist, oder das Concept ganz meiden und stattdessen auf eine Rückfrage beim Prüfungsamt verweisen.
- Fehlt `status` → gilt als `stable` (Spec-Default), normal verwendbar.

### 2.2 Aktualität prüfen (`stale_after`, §5.5)

- Aktuelles Datum mit `stale_after` vergleichen: `heute >= stale_after` ⇒ **veraltet**.
- Veraltete Concepts nicht aktiv für die Antwort nutzen. Falls keine aktuellere Quelle verfügbar ist, den Nutzer/die Empfängerin explizit auf die mögliche Veraltung hinweisen, statt die Information kommentarlos als gültig auszugeben.

### 2.3 Vertrauensstufe prüfen (`verified`, §5.2/§5.3)

Trust-Tier ableiten (niedrig → hoch):

- Kein `verified`-Feld ⇒ **unverified**. In der Antwort vorsichtig formulieren ("nach aktuellem Stand", "in der Regel") oder auf eine Rückfrage bei der zuständigen Stelle verweisen.
- `verified` nur durch `process:`- oder Agenten-Actors ⇒ **machine-confirmed**. Mit angemessener Sorgfalt verwendbar, bei rechtlich heiklen Themen (Prüfungsordnung, Fristen) trotzdem mit Formulierungsvorbehalt versehen.
- `verified` durch mindestens einen `human:<id>`-Actor ⇒ **human-reviewed**. Höchste Stufe.

**Wichtig — kein Automatismus:** `human-reviewed` bedeutet **nicht**, dass 2.1 und 2.2 übersprungen werden dürfen. Trust Tiers sind laut Spec "advisory signals, not access control" (§5.3) — ein human-reviewed Concept kann trotzdem `deprecated` oder `stale_after`-abgelaufen sein. **Alle drei Prüfungen (Status, Aktualität, Trust) sind immer gemeinsam auszuführen**, keine ersetzt die andere.

### 2.4 Herkunft dokumentieren (`sources`, §5.1)

- Für jede sachliche Aussage die zugehörige `sources`-Entry identifizieren.
- Falls im Concept-Body eine Fußnote (`[^id]`) verwendet wird, deren Ziel über die `id` in `sources` auflösen — **nicht** die Fußnoten-Prosa im Body als alleinige Quelle nehmen, sondern über den `id`-Join-Key auf den strukturierten `sources`-Eintrag zurückgreifen.
- In der generierten E-Mail-Antwort die Quelle konkret benennen (Dokumenttitel + Paragraph/Abschnitt, falls vorhanden), z. B.:
  > "… spätestens jedoch innerhalb von 3 Werktagen (§ 15 Prüfungsordnung). [1]"
  > **Quelle:** [1] Prüfungsordnung, hinterlegt in `/documents/examination-guidelines.md`
- Enthält ein Concept keine `sources`, darf die Aussage trotzdem verwendet werden (§11: fehlende optionale Felder sind kein Ablehnungsgrund) — dann aber ohne Quellenverweis und mit entsprechend vorsichtigerer Formulierung.

## 3. Berechnungen: NIEMALS selbst rechnen — immer über Attested Computation, IMMER attestieren

Dies ist der Punkt, an dem die bisherige Projekt-Doku unvollständig war. Die vollständige Pipeline aus §10.5 hat **sechs** Schritte — Schritte 1–4 sind in der bisherigen Doku beschrieben, **Schritt 5 (Attest) und 6 (Gate) fehlten** und sind hier verpflichtend nachzuholen:

1. **Discover:** Concept vom `type: Attested Computation` identifizieren (über `index.md` oder Link aus einem verweisenden Concept).
2. **Load:** Contract-Felder aus der Frontmatter laden (`runtime`, `parameters`, `executor`, `attester`) sowie die Berechnung selbst (Body-Fence unter `# Computation`, oder die per `computation`-Feld referenzierte Datei).
3. **Parameterize:** Nur Werte für die deklarierten `parameters` einsetzen. Der Agent darf die Berechnung selbst **nicht** verändern, erweitern oder neu formulieren — auch nicht "nur um sie verständlicher zu machen".
4. **Execute:** Die Berechnung über den in `executor.resource` benannten Runner ausführen lassen (Skript, Query, o. ä.) und das `receipt` gemäß `executor.receipt` entgegennehmen (z. B. `job_id`, `executed_sql`, `result`).
5. **Attest (bisher fehlend — jetzt verpflichtend):** Das `receipt` **muss** durch den in `attester.resource` benannten, deterministischen Prüfer laufen, bevor das Ergebnis verwendet wird. Der Attester bestätigt zwei Dinge unabhängig: (a) dass tatsächlich die sanktionierte Berechnung gelaufen ist und keine vom Agenten selbst geschriebene/veränderte Query, und (b) dass der im Entwurf verwendete Wert exakt dem im Receipt belegten Ergebnis entspricht.
6. **Gate (bisher fehlend — jetzt verpflichtend):** Schlägt die Attestierung fehl, **darf das Ergebnis nicht in die E-Mail übernommen werden.** Stattdessen: Fehler kommunizieren bzw. die E-Mail für eine manuelle Bearbeitung markieren. Ebenso: Ist die zugehörige `Attested Computation` selbst `stale_after`-abgelaufen (siehe 2.2), muss vor Verwendung gewarnt oder die Verwendung verweigert werden.

**Merksatz für den Agenten:** *Ein `receipt` ohne erfolgreiche Attestierung ist noch kein verwendbares Ergebnis — es ist eine unbestätigte Behauptung des Executors.* Erst der Attester macht daraus einen belastbaren Wert. Verifikation der Definition (`verified`, Schritt 2.3) und Attestierung eines konkreten Laufs (Schritt 5) sind laut §10.6 zwei unabhängige Dinge — ein frisch verifiziertes Concept ersetzt nicht die Attestierung des einzelnen Laufs, und umgekehrt.

## 4. Formulierungsregeln für den E-Mail-Entwurf

- Jede Aussage, die aus einem `unverified`- oder `machine-confirmed`-Concept stammt, sprachlich als Auskunft "nach aktuellem Kenntnisstand" kennzeichnen, nicht als unumstößliche Zusage.
- Bei `human-reviewed`-Concepts, die zusätzlich frisch (nicht `stale_after`) und `stable`/ohne `status`-Konflikt sind, kann die Aussage direkt und ohne Einschränkung formuliert werden.
- Rechnerische Ergebnisse (Fristen, Notenschnitte, ECTS-Hürden) ausschließlich als Ergebnis einer erfolgreich attestierten `Attested Computation` einbinden (siehe Abschnitt 3) — niemals als eigenständig vom LLM ausgerechneter Wert, auch nicht als "Kontrollrechnung" oder Näherung.
- Am Ende der E-Mail bei rechtlich/administrativ relevanten Aussagen die verwendete(n) Quelle(n) nennen (Abschnitt 2.4).
- Ist für eine Frage kein passendes Concept auffindbar (auch nicht über Graph-Links), das offen kommunizieren ("kann ich anhand der vorliegenden Unterlagen nicht abschließend beantworten") statt eine plausible, aber unbelegte Antwort zu generieren.

## 5. Kurz-Checkliste (vor dem Versenden/Vorlegen eines Entwurfs)

- [ ] Wurde jedes verwendete Concept über `index.md`/Links gezielt geladen, nicht pauschal das ganze Bundle?
- [ ] Wurde für jedes verwendete Concept `status` geprüft (kein `deprecated`/`draft` als finale Aussage zitiert)?
- [ ] Wurde für jedes verwendete Concept `stale_after` gegen das heutige Datum geprüft?
- [ ] Wurde die Trust-Tier-Einstufung (`verified`) korrekt in die Formulierung übersetzt — unabhängig von 2. und 3., nicht als Ersatz dafür?
- [ ] Ist jede sachliche Aussage einer `sources`-Quelle zuordenbar und wird diese in der Antwort genannt?
- [ ] Enthält die E-Mail Berechnungsergebnisse? Falls ja: Wurden sie über eine `Attested Computation` mit **erfolgreicher Attestierung** (nicht nur Executor-`receipt`) erzeugt?
- [ ] Wurde bei fehlgeschlagener Attestierung oder abgelaufener `stale_after` das Ergebnis **nicht** verwendet, sondern eskaliert?
