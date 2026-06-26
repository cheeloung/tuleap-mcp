# Tuleap MCP Server

[![CI](https://github.com/cheeloung/tuleap-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/cheeloung/tuleap-mcp/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

A secure, fully-tested **Model Context Protocol (MCP)** server for interacting with [Tuleap](https://tuleap.net/). This allows your favorite AI assistants (Claude, OpenCode, Cursor, Gemini, etc.) to safely read and manage your Agile projects, track artifacts, list Git repositories, and query users directly from your IDE or chat interface.

---

## Features

- **Agile & Projects**: Search projects, retrieve Epics, list User Stories, create new Epics or User Stories, get Epic progress, list milestones.
- **Trackers & Artifacts**: Search artifacts with flexible filters, get field definitions, create and update artifacts, read comments, list artifacts by assignee.
- **Files & Repositories**: List Git repositories linked to a project.
- **Users**: Search for Tuleap users by name or email.

## Security & Best Practices

- **Zero Hardcoded Secrets**: Tokens are passed strictly via your local environment variables.
- **No Personal Data Logging**: The server acts purely as a conduit and does not cache or log your Tuleap data.
- **Automated Security Scans**: CI pipelines run `bandit` to ensure no common vulnerabilities are introduced.
- **Test-Driven**: Comprehensive tests with `pytest` and `respx` ensure data is mocked accurately without hitting live environments.

---

## Prerequisites & Installation

1. **Prerequisites**:
   - Python 3.10 or higher.
   - A Tuleap instance URL.
   - A Tuleap Personal Access Token (API Key) generated via Tuleap user settings.

2. **Clone & Setup**:
   ```bash
   git clone https://github.com/cheeloung/tuleap-mcp.git
   cd tuleap-mcp

   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```

3. **Verify Executable Path**:
   ```
   /absolute/path/to/tuleap-mcp/.venv/bin/tuleap-mcp
   ```

---

## Configuration & Usage

### Using with Claude Desktop

Add this to your `claude_desktop_config.json` (typically `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "tuleap": {
      "command": "/absolute/path/to/tuleap-mcp/.venv/bin/tuleap-mcp",
      "env": {
        "TULEAP_URL": "https://your-tuleap-instance.com",
        "TULEAP_API_KEY": "your-tuleap-api-key"
      }
    }
  }
}
```

### Using with OpenCode

```json
{
  "mcp": {
    "tuleap": {
      "type": "local",
      "command": ["/absolute/path/to/tuleap-mcp/.venv/bin/tuleap-mcp"],
      "environment": {
        "TULEAP_URL": "https://your-tuleap-instance.com",
        "TULEAP_API_KEY": "your-tuleap-api-key"
      },
      "enabled": true
    }
  }
}
```

### Using with Gemini / Cursor / Zed

Point the MCP settings to the full path of `.venv/bin/tuleap-mcp` and inject `TULEAP_URL` and `TULEAP_API_KEY` as environment variables.

---

## AI System Prompt

For the best experience, give your AI assistant a system prompt that teaches it how to use this MCP effectively — including how to resolve IDs to human-readable names and which tool to call first for each task.

The full prompt is in [`docs/system-prompt.md`](docs/system-prompt.md). Key behaviours it enables:

- **Context file** (`tuleap-context.md`): The AI maintains a local markdown file mapping project/tracker/user/group IDs to names. It reads this at the start of each session and updates it as new IDs are encountered, so responses always show names instead of raw numbers.
- **Discovery-first**: The AI always calls `get_tracker_fields` before creating or updating artifacts, so it never guesses field IDs or bind values.
- **Guided workflows**: Step-by-step instructions for common tasks — listing my tasks, creating an artifact, updating status, checking sprint content, reviewing epic progress.
- **Field mapping rules**: Explicit rules for when to use `bind_value_ids` vs `value`, and how to handle field dependency errors (e.g. Assigned To → User Group).

### Context file format

The AI keeps a local `tuleap-context.md` in your working directory (not committed to source control):

```markdown
# Tuleap Context

## Projects
| ID | Name | Shortname |
|----|------|-----------|
| 103 | AMAG SCH | amag-sch |

## Trackers
| ID | Name | Project |
|----|------|---------|
| 67 | 04. Tasks | AMAG CP Testing |

## Users
| ID | Display Name | Username |
|----|-------------|----------|
| 119 | Chee Loung Cheah | cheeloung.cheah |

## User Groups
| ID | Name |
|----|------|
| 107 | SwE |
```

---

## Available MCP Tools

### Projects & Trackers
| Tool | Description |
|------|-------------|
| `search_projects(query?)` | List projects you are a member of, optionally filtered by shortname |
| `get_project_trackers(project_id)` | List all trackers in a project |
| `get_tracker_fields(tracker_id)` | List field IDs, types, required flag, and allowed values — call this before create/update |

### Artifacts
| Tool | Description |
|------|-------------|
| `search_artifacts(tracker_id, filters?)` | Search artifacts with optional filters e.g. `{"assigned_to": {"id": 119}}` |
| `get_artifact(artifact_id)` | Get slim details: id, title, status, assigned_to, last_modified_date |
| `get_artifact_comments(artifact_id)` | Get all comments on an artifact |
| `create_artifact(tracker_id, values)` | Create a new artifact |
| `update_artifact(artifact_id, values?, comment?)` | Update fields or add a comment |
| `get_my_artifacts(user_id, tracker_id)` | List artifacts assigned to a specific user |

### Agile
| Tool | Description |
|------|-------------|
| `get_project_epics(project_id)` | List epics for a project |
| `get_epic_progress(epic_id)` | Get Status, Progress, and Effort summary for an epic |
| `create_epic(project_id, values)` | Create a new epic |
| `get_project_user_stories(project_id, epic_id?)` | List user stories, optionally filtered by parent epic |
| `create_user_story(project_id, values)` | Create a new user story |
| `link_to_epic(epic_id, child_artifact_id)` | Link a child artifact to a parent epic |
| `get_project_milestones(project_id, status?)` | List milestones (releases/sprints), filter by `open` or `closed` |

### Users & Git
| Tool | Description |
|------|-------------|
| `search_users(query?)` | Search users by name, username, or email |
| `get_git_repos(project_id)` | List git repositories linked to a project |

---

## Development & Contributing

```bash
source .venv/bin/activate
pip install -e ".[dev]"

# Run tests with coverage
pytest --cov=src/tuleap_mcp tests/

# Lint and format
ruff check .
ruff format .

# Security scan
bandit -r src/
```

### CI/CD Pipeline
Every Pull Request runs a GitHub Actions workflow ensuring:
1. All unit tests pass.
2. Code follows Ruff formatting rules.
3. Bandit flags no common security issues.

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
