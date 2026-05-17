# Changelog Workflow

We use **Conventional Commits** and **git-cliff** to automatically maintain our changelog.

## Commit Message Format

Messages should follow this pattern:

```text
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**  
- `feat`: A new feature  
- `fix`: A bug fix  
- `docs`: Documentation changes  
- `style`: Changes to format/styling (no code effect)  
- `refactor`: Code change that neither fixes a bug nor adds a feature  
- `perf`: Performance improvements  
- `test`: Adding or correcting tests  
- `chore`: Changes to the build process or utilities  

## Automation

With every release (push of a tag `v*`), the GitHub Action runs `git-cliff`, updates the `CHANGELOG.md` file in the root directory, and creates a GitHub Release.
