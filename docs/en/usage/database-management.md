# Database Management (`db`)

The `db` command group allows direct management of metadata and the search index.

## Listing Content
You can list various entities in the database:

*   **Files:** `mcp-uni db list-files`  
*   **Folders:** `mcp-uni db list-folders`  
*   **Students:** `mcp-uni db list-students` (Note: Use `sync-students` to populate)  
*   **Summaries:** `mcp-uni db list-summaries`  
*   **Deadlines:** `mcp-uni db list-deadlines`  

## Synchronizing Students (`sync-students`)
Populates the database from a `students.yaml`.
```bash
mcp-uni db sync-students
```

## Deleting Content
Entries can be deleted by their ID. With the `--force` or `-f` option, the confirmation prompt is skipped.

*   **Delete files:** `mcp-uni db delete-file <ID_1> <ID_2> ...`  
*   **Delete folder:** `mcp-uni db delete-folder <ID>` (recursively removes all contained files)  
*   **Delete student:** `mcp-uni db delete-student <ID>`  
*   **Delete summary:** `mcp-uni db delete-summary <ID>`  
*   **Delete deadline:** `mcp-uni db delete-deadline <ID>`  

## Knowledge Graph Management
You can directly manage the nodes and edges of the Knowledge Graph:

*   **List nodes:** `mcp-uni db list-nodes`
*   **List edges:** `mcp-uni db list-edges`
*   **Delete node:** `mcp-uni db delete-node <ID>` (also removes all associated edges)
*   **Delete edge:** `mcp-uni db delete-edge <ID>`

## Manual Troubleshooting
For complex manual corrections or direct editing of the database, we recommend external tools such as:
*   **[DB Browser for SQLite](https://sqlitebrowser.org/)**: A user-friendly open-source tool for viewing, editing, and querying SQLite databases.

Simply open the `.db` file specified in your configuration (default: `data/university.db`) in DB Browser for SQLite.
