# Qualitäts-Metriken

Diese Seite visualisiert die aktuellen Qualitätsmetriken des Projekts. Die Daten werden bei jedem CI-Lauf aktualisiert.

## Projektübersicht

<div id="metrics-container">
  <p>Lade Metriken...</p>
</div>

<script>
fetch('../assets/metrics.json')
  .then(response => response.json())
  .then(data => {
    const container = document.getElementById('metrics-container');
    container.innerHTML = `
      <table style="width: 100%">
        <thead>
          <tr>
            <th>Metrik</th>
            <th>Wert</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Docstring Coverage</td>
            <td>${data.interrogate_coverage}%</td>
            <td>${Number(data.interrogate_coverage) >= 95 ? '✅ Pass' : '❌ Fail'}</td>
          </tr>
          <tr>
            <td>Markdown Lint</td>
            <td>${data.markdownlint_errors} Fehler</td>
            <td>${Number(data.markdownlint_errors) === 0 ? '✅ Clean' : '⚠️ Attention'}</td>
          </tr>
          <tr>
            <td>Broken Links</td>
            <td>${data.broken_links}</td>
            <td>${Number(data.broken_links) === 0 ? '✅ All good' : '❌ Fix needed'}</td>
          </tr>
          <tr>
            <td>Build Warnings</td>
            <td>${data.build_warnings}</td>
            <td>${Number(data.build_warnings) === 0 ? '✅ Perfect' : '⚠️ Review'}</td>
          </tr>
        </tbody>
      </table>
      <p><small>Zuletzt aktualisiert: ${new Date(data.timestamp * 1000).toLocaleString()}</small></p>
    `;
  })
  .catch(err => {
    document.getElementById('metrics-container').innerHTML = '<p>Metrik-Daten zur Zeit nicht verfügbar (nur im Deployment sichtbar).</p>';
  });
</script>

## Erläuterung

*   **Docstring Coverage:** Anteil der Klassen und Methoden mit validen Google-Style Docstrings.  
*   **Markdown Lint:** Überprüfung auf Formatierungsfehler in den Dokumentationsdateien.  
*   **Broken Links:** Automatische Prüfung aller internen und externen Links.  
*   **Build Warnings:** Warnungen des MkDocs Build-Prozesses (z.B. fehlende Dateien in der Navigation).  
