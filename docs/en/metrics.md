# Quality Metrics

This page visualizes the current quality metrics of the project. Data is updated during every CI run.

## Project Overview

<div id="metrics-container">
  <p>Loading metrics...</p>
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
            <th>Metric</th>
            <th>Value</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Docstring Coverage</td>
            <td>${data.interrogate_coverage}%</td>
            <td>${data.interrogate_coverage >= 95 ? '✅ Pass' : '❌ Fail'}</td>
          </tr>
          <tr>
            <td>Markdown Lint</td>
            <td>${data.markdownlint_errors} errors</td>
            <td>${data.markdownlint_errors === 0 ? '✅ Clean' : '⚠️ Attention'}</td>
          </tr>
          <tr>
            <td>Broken Links</td>
            <td>${data.broken_links}</td>
            <td>${data.broken_links === 0 ? '✅ All good' : '❌ Fix needed'}</td>
          </tr>
          <tr>
            <td>Build Warnings</td>
            <td>${data.build_warnings}</td>
            <td>${data.build_warnings === 0 ? '✅ Perfect' : '⚠️ Review'}</td>
          </tr>
        </tbody>
      </table>
      <p><small>Last updated: ${new Date(data.timestamp * 1000).toLocaleString()}</small></p>
    `;
  })
  .catch(err => {
    document.getElementById('metrics-container').innerHTML = '<p>Metric data currently unavailable (only visible in deployment).</p>';
  });
</script>

## Explanation

*   **Docstring Coverage:** Percentage of classes and methods with valid Google-style docstrings.  
*   **Markdown Lint:** Check for formatting errors in the documentation files.  
*   **Broken Links:** Automatic check of all internal and external links.  
*   **Build Warnings:** Warnings from the MkDocs build process (e.g., missing files in navigation).  
