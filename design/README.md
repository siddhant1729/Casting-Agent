# Design reference

The Stitch export the frontend was built against.

    Project: AI Casting Agent Interface (11313793131988014355)
    Screen:  Casting Screen - HexCoded (d4c17002e02b490db4c074b97804edfd)

| File | |
|---|---|
| `casting-screen.png` | Full-resolution screen, 2560×3574. The download URL serves a 367×512 thumbnail unless `=s0` is appended. |
| `casting-screen.html` | The generated markup. Source of truth for the palette and type scale — the values in `frontend/src/index.css` are lifted from its Tailwind config, not sampled off the image. |

Tracked in git on purpose: a checkout without it cannot be reviewed against the design.

Treated as a visual reference only. Components are written against the real API in
`backend/casting/api.py`; nothing here is pasted.

## Fetching it again

There is no Stitch connector loaded in a fresh Claude Code session even when the MCP server
is configured — MCP tools bind at session start. The endpoint is plain JSON-RPC over HTTP,
so it can be driven directly:

```bash
KEY=...   # X-Goog-Api-Key
curl -s -X POST https://stitch.googleapis.com/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "X-Goog-Api-Key: $KEY" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{
        "name":"get_screen",
        "arguments":{"projectId":"11313793131988014355",
                     "screenId":"d4c17002e02b490db4c074b97804edfd"}}}'
```

The response carries `screenshot.downloadUrl` and `htmlCode.downloadUrl`.

## What was not built from it

Regions 2 and 4 of the design — the editable attribute chips, the tonal risk slider, the
"12 looks not shown" panel, and the counterfactual empty-state engine — need backend
capabilities this API does not have. See *What the design specifies and this does not
build* in the root README.

Anything implying cost, pricing, availability dates, reservations or warning callouts is
dropped rather than built.
