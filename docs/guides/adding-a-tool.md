# Adding a New Tool to Kit

**Status:** Living playbook. Updated whenever the pattern evolves.
**Based on:** `route`, `cal`, `flights` modules.

---

## 1. Terminology

You asked what to call this. Here's the vocabulary Kit uses consistently:

| Term | Meaning | Example |
|---|---|---|
| **Tool** (Kit-internal) | A self-contained module under `src/kit/<name>/` exposing functionality through three interfaces: CLI, Python API, MCP. | `flights`, `route`, `cal` |
| **Tool** (MCP) | A single callable registered with the MCP server, invoked by Claude. One Kit tool usually registers several MCP tools. | `kit_route`, `kit_flight_search` |
| **Service** | An external thing Kit talks to (Ryanair API, Google Maps, Google Calendar). Not a Kit tool. | Ryanair fare API |
| **Client** | The class inside a Kit tool that wraps the external service. | `RyanairFareClient`, `GoogleMapsRouter` |
| **Actor** (Apify-specific) | An Apify-hosted scraper you invoke via their API. Kit doesn't use any right now. | — |
| **Integration** | Cross-tool interaction (e.g. `cal` using `route` for travel buffers). | — |

Rule of thumb: "**tool**" without qualifier = Kit-internal tool (the five-file module). When you need to disambiguate, say **MCP tool** or **external service**.

## 2. When to add a Kit tool vs. register an external MCP

Two levels:

**Just register a remote MCP in `~/.claude/settings.json`** — when you want Claude to have the capability but don't need CLI access, Python API, or integration with other Kit tools. Zero code, fastest win.

**Build a full Kit tool** — when any of these apply:
- You want a `kit <name>` CLI command.
- You want to call it from scripts as `from kit.name import ...`.
- You want it to integrate with route / cal / plan_day (present or future).
- The external service's API is awkward (bad schema, paid, unstable) and you want a clean internal contract.
- You want typed Pydantic models and tests that don't hit the network.

`flights` is a case study: first attempt used Apify's MCP endpoint for zero code. The actor turned out to be paid, so we pivoted to a full Kit tool calling Ryanair's public API directly. The Kit-tool layer gave us a stable internal contract independent of the underlying service.

## 3. The five-file pattern

Every Kit tool lives at `src/kit/<name>/` with these files:

```
src/kit/<name>/
├── __init__.py        # re-exports the user-facing API
├── core.py            # Pydantic models: <Name>Request, <Name>Result
├── <service>.py       # Client class wrapping the external service
├── planner.py         # High-level orchestrator: validates, calls client, shapes result
├── commands.py        # Typer subcommand(s) for `kit <name> ...`
└── mcp_tools.py       # register_<name>_tools(mcp, config) + @mcp.tool() wrappers
```

And four corresponding test files in `tests/`:
```
tests/
├── test_<name>_core.py       # Model validation
├── test_<name>_<service>.py  # Client — mocked HTTP
├── test_<name>_planner.py    # Orchestrator — mocked client
└── test_mcp_<name>.py        # MCP tool wiring
```

All existing tools follow this. Don't invent variations without a reason.

## 4. Step-by-step

### 4.1 Before writing code

1. **Decide scope.** Full tool or just a remote MCP? See §2.
2. **Pick the external service.** If there's a public API, prefer it over scrapers/actors — cheaper, more stable.
3. **Probe the service.** Hit it with `httpx` in a throwaway script. Capture a real response. This tells you the shape of your Pydantic models before you write them.
4. **Check auth.** Token needed? If yes, add a field to `KitConfig` (`src/kit/config.py`) with both env-var default and TOML load path. If no, skip this.

### 4.2 Create the module

Order matters — each step depends on the previous.

1. **`core.py`**: Pydantic models for the request and result. Validators go here (e.g. `date_to >= date_from`). Use `Literal` for enumerated fields.
2. **`<service>.py`**: Client class. One class, one method (`run_search`, `fetch`, etc.) returning parsed domain objects. Map HTTP errors to `KitError` subclasses. Inject `httpx.Client` as a constructor arg for testability.
3. **`planner.py`**: High-level function (`search_flights`, `plan_route`, `add_event`). Orchestrates: build/load config → instantiate client → call client → shape result. This is what users of the Python API import.
4. **`commands.py`**: Typer subcommand. Parse CLI args → build the Pydantic request → call the planner → render output (Rich table default, `--json` for agents). Mirror `src/kit/route/commands.py`'s `_DefaultTo<Subcommand>Group` pattern.
5. **`mcp_tools.py`**: `register_<name>_tools(mcp: FastMCP, config: KitConfig)` function. Wrap each user-facing planner call in a `@mcp.tool()` decorator with clear docstring + typed args. Return `result.model_dump_json(indent=2)`.
6. **`__init__.py`**: Re-export the user-facing surface (`from kit.<name>.core import ...` + `from kit.<name>.planner import ...`) and list in `__all__`.

### 4.3 Wire it in

Three places — one line each:

1. **`src/kit/cli.py`**: `from kit.<name>.commands import <name>_app` + `app.add_typer(<name>_app, name="<name>")`.
2. **`src/kit/mcp_server.py`**: `from kit.<name>.mcp_tools import register_<name>_tools` + `register_<name>_tools(mcp, config)`.
3. **`src/kit/errors.py`**: add a domain error class if needed (e.g. `FlightSearchError(KitError)`).

### 4.4 Tests

1. Write tests **alongside** implementation (TDD-adjacent — full TDD is fine, but at least don't defer them).
2. Mock at the boundary: `MagicMock(spec=httpx.Client)` for the service, `MagicMock()` for the client in planner tests.
3. For MCP tool tests, use `FastMCP("test")` + `register_<name>_tools` + iterate `mcp._tool_manager._tools` to find the registered function.
4. Add your MCP tool name to the `expected = {...}` set in `tests/test_mcp_server.py::test_mcp_server_has_all_tools`.
5. Real-API smoke tests: mark with `@pytest.mark.smoke` so `-m "not smoke"` skips them in CI.

### 4.5 Verify

```bash
pytest -v -m "not smoke"         # all green
ruff check src/kit/<name>/       # clean
mypy src/kit/<name>/              # clean (pre-existing config.py noise is OK)
kit <name> --help                # subcommand shows up
kit <name> <subcmd> ...          # real call works
```

Then restart Claude Code and verify the MCP tool shows up (ask Claude about it in a new session).

### 4.6 Document

1. Write a spec at `docs/specs/YYYY-MM-DD-kit-<name>.md` describing architecture, transport, data model, out-of-scope.
2. If the new tool reveals a cross-cutting architectural question (like `flights` did about calendar integration), drop a separate note at `docs/specs/YYYY-MM-DD-<topic>.md` — don't bake the decision into the tool.

## 5. Common pitfalls

| Pitfall | Symptom | Fix |
|---|---|---|
| `kit` command fails with `ModuleNotFoundError: kit` | macOS sandbox re-applies UF_HIDDEN to editable `.pth` files. | Symlink `src/kit` directly into the venv's `site-packages/`: `ln -sfn $(pwd)/src/kit .venv/lib/python*/site-packages/kit` |
| Pytest can't find `kit` | Same root cause. | `pyproject.toml` has `[tool.pytest.ini_options] pythonpath = ["src"]` — keep it. |
| External API 403s your requests | Missing or default User-Agent. | Pass a browser-like `User-Agent` header in the client's default headers. |
| Service returns "no flights" but their UI does | Service returns data per-month; your query spans months. | Loop over months, concatenate, then filter to the requested window. |
| MCP tool doesn't show up in Claude Code | Server wasn't re-read after code change. | Restart Claude Code (MCP servers load at session start). |
| Cross-tool integration creeps into every tool | Bespoke coupling between N tools grows N². | Keep v1 standalone. Lift integration into a shared contract (see `docs/specs/2026-04-18-cross-tool-integration-hooks.md`) before wiring the second cross-tool scenario. |

## 6. Reference implementations

When in doubt, copy the pattern from the closest existing tool:

- **Simple read-only service with auth**: `src/kit/route/` (Google Maps SDK).
- **Service with complex write operations**: `src/kit/cal/` (Google Calendar, OAuth).
- **Public API, no auth, month-at-a-time paging**: `src/kit/flights/` (Ryanair).

## 7. Decision log

Kept here so future tools don't re-litigate:

- **Auth goes in `KitConfig`** with env-var override, not in per-tool config. Fewer places to look.
- **Clients take `httpx.Client` via constructor**, never create it at call time. Testability + connection reuse.
- **Planner takes `client` as an optional arg**, defaulting to a fresh instance. Tests inject a mock; production code uses default.
- **MCP tools return `result.model_dump_json(indent=2)` as a string**. FastMCP expects strings.
- **CLI default subcommand**: each Typer group has a `_DefaultTo<X>Group` so `kit flights BER DUB ...` works without typing `search`.
- **`--json` flag** on every CLI command for agent consumption.
- **Errors**: domain-specific subclasses of `KitError`. CLI maps to exit codes, MCP raises — FastMCP serializes.
