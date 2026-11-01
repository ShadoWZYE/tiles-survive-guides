# User-entered chat formatting: code findings

Checked 31 October 2026. Native client 2.6.300.293; downloaded chat prefab revision 2.6.300.301. Static inspection only; no messages sent.

## Confirmed on the user-message path

- Ordinary player message widgets (`p_text_message`) use the custom `RichText` class with `m_FontData.m_RichText = 1`. This is the actual chat message body, not just a game-generated heading.
- `ChatItemProBase.UpdateMessage` obtains the message via `ChatDataEx.GetDisplayText`, passes it through `EmojiModule.ConvertEmoji`, then assigns it to the message text component.
- The emoji parser recognises `#` followed by exactly three digits and generates internal image quads for configured emoji. Example syntax: `#066`. The parser also tokenises existing angle tags; that does not establish that typed tags survive the full service pipeline.

## Explicit user-tag escaping

`ChatModule.MakeMessage` calls `Utils.EscapeRichTextWithZeroWidth` before displaying the immediate local copy of a sent message. Its recovered regex and replacement are:

```text
Pattern:     (<)([^\s|<]+)
Replacement: < $2
Input:       <b>TEST</b>
Local echo:  < b>TEST< /b>
```

The recovered replacement contains an ordinary ASCII space despite the method name. This neutralises tag opening syntax. The local-copy branch is skipped when `FilterSelfChat` is enabled. The packet is built before this local-copy escaping call; recipient/server processing has not been established.

## What this means for bold, italic and colour

The renderer is rich-text capable, but that is not proof of an unrestricted player formatting feature. There is explicit code to neutralise typed angle tags on the sender local echo. Recipient output can only be confirmed by checking server/SDK processing or a received message; the local send preview is insufficient. No evidence was established for Markdown or BBCode conversion.

Player-entered `#NNN` emoji codes are code-backed. Claims that `<b>`, `<i>` or `<color=...>` definitely work for everyone are not yet justified, nor is a blanket claim that no recipient can ever see formatting.

## Evidence pointers

- `ChatModule.MakeMessage`: RVA `0x39471d0`; escape call `0x394740f`.
- `Utils.EscapeRichTextWithZeroWidth`: RVA `0x3321cb0`; literal regex `1475`, replacement `3422`.
- `ChatItemProBase.UpdateMessage`: RVA `0x3974570`.
- `EmojiModule.ConvertEmoji`: RVA `0xc37850`; static regex literal `1477`.
- Chat prefab bundle `2228adf83d3bdcfde5aeb4b0fbd8d62c`, component path ID `-2455681222521827788`.

Runtime hotfixes, server filtering and differences between chat channels remain unverified. Raw extraction and method hashes are retained privately under `tmp/chat-format-audit`.
