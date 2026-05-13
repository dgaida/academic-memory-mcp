# Versioning

Documentation is versioned with **mike** to provide different states of the project (e.g., `latest`, `dev`, `v0.1.0`) simultaneously.

## Deployment Strategy

1.  **Main Branch:** Every push to `main` updates the `dev` version of the documentation.
2.  **Tags:** Every tag (`v*`) creates a new permanent version and updates the `latest` alias.

## Manual Deployment

To build a version locally and push it to `gh-pages`:

```bash
mike deploy --push --update-aliases 0.1.0 latest
mike set-default --push latest
```

## Version Selector

The version selector is located in the header of the documentation. It allows users to quickly switch between stable releases and the current development state.
