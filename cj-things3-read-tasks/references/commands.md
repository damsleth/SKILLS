# things-cli Commands

This reference is derived from `things-cli --help` and `things-cli search --help`.

## Core Commands

- `things-cli today`
- `things-cli search "<string>"`
- `things-cli -j todos`

## List/State Commands

- `inbox`
- `today`
- `upcoming`
- `anytime`
- `completed`
- `someday`
- `canceled`
- `trash`
- `todos`
- `all`

## Organization Commands

- `areas`
- `projects`
- `tags`

## Activity/Date Commands

- `logbook`
- `logtoday`
- `createdtoday`
- `deadlines`

## Other Commands

- `feedback`
- `search <string>`

## Global Flags

- `-j, --json`: Output as JSON.
- `-c, --csv`: Output as CSV.
- `-o, --opml`: Output as OPML.
- `-g, --gantt`: Output as Mermaid Gantt.
- `-r, --recursive`: In-depth output.
- `-p, --filter-project <name>`: Filter by project.
- `-a, --filter-area <name>`: Filter by area.
- `-t, --filtertag <name>`: Filter by tag.
- `-e, --only-projects`: Export only projects.
- `-d, --database <path>`: Set a custom Things database path.
- `-v, --version`: Show version.

## Search Command Usage

```bash
things-cli search "<string>"
```

`search` requires one positional string argument.
