#!/usr/bin/env python3
"""Convert a Markdown file to Nexus-flavoured BBCode.

Parses the source with markdown-it-py (a CommonMark-compliant parser, plus
GFM tables and ~~strikethrough~~) and walks the resulting syntax tree, emitting
the BBCode tags the Nexus Mods description editor understands. Because a real
parser does the reading, nested emphasis, links inside list items, fenced code,
block quotes and the rest all round-trip correctly rather than relying on
brittle regex passes.

Usage:
    python tools/md2bbcode.py                 # README.md -> dist/<name>-nexus.bbcode
    python tools/md2bbcode.py CHANGELOG.md    # pick a different source
    python tools/md2bbcode.py README.md -o out.txt
    python tools/md2bbcode.py --stdout        # print instead of writing a file

The tag mapping lives in the constants below - tweak them if Nexus changes
which BBCode it accepts, or to suit a different forum's dialect.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    from markdown_it import MarkdownIt
    from markdown_it.tree import SyntaxTreeNode
except ImportError:  # pragma: no cover - friendly bail-out
    sys.exit(
        "markdown-it-py is required. Install it with:\n"
        "    python -m pip install markdown-it-py\n"
        "(or: python -m pip install -r tools/requirements.txt)"
    )

# ---- BBCode dialect -------------------------------------------------------
# Nexus has no <h1>..<h6>; map heading levels onto [size]+[b]. Deeper headings
# just get bold. Adjust the size numbers here if your headings look off on the
# live page - Nexus's size scale is relative, not pixels.
HEADINGS: dict[int, tuple[str, str]] = {
    1: ("[size=6][b]", "[/b][/size]"),
    2: ("[size=5][b]", "[/b][/size]"),
    3: ("[size=4][b]", "[/b][/size]"),
    4: ("[size=3][b]", "[/b][/size]"),
    5: ("[b]", "[/b]"),
    6: ("[b]", "[/b]"),
}
INLINE_CODE = ("[font=Courier New]", "[/font]")  # Nexus has no inline <code>
HORIZONTAL_RULE = "[line]"
SPOILER = ("[spoiler]", "[/spoiler]")  # Nexus hides the text until clicked

LIST_TYPES = ("bullet_list", "ordered_list")

# <div> means nothing to Nexus, but an aligned wrapper is a common README idiom,
# so translate <div align="center|left|right|justify"> ... </div> into the
# matching [center]/[left]/[right]/[justify] block and let every other <div>
# pass through untouched. Quote style and spacing vary in the wild, hence the
# tolerant patterns: DIV_TAG_RE finds each opening/closing div tag in order;
# DIV_ALIGN_RE pulls the alignment out of an opening tag.
ALIGN_TAGS: dict[str, tuple[str, str]] = {
    "center": ("[center]", "[/center]"),
    "left": ("[left]", "[/left]"),
    "right": ("[right]", "[/right]"),
    "justify": ("[justify]", "[/justify]"),
}
DIV_TAG_RE = re.compile(r"<div\b[^>]*>|</div\s*>", re.IGNORECASE)
DIV_ALIGN_RE = re.compile(
    r"""align\s*=\s*['"]?\s*(center|left|right|justify)\b""", re.IGNORECASE
)


class BBCodeRenderer:
    """Walk a markdown-it syntax tree and produce BBCode."""

    # -- entry point --------------------------------------------------------
    def render(self, root: SyntaxTreeNode) -> str:
        self._div_stack: list[str | None] = []  # per open <div>: its close tag
        return self._blocks(root.children)

    # -- block level --------------------------------------------------------
    def _blocks(self, nodes, sep: str = "\n\n") -> str:
        """Render a sequence of block nodes, blank-line separated."""
        parts = [self._block(n) for n in nodes]
        return sep.join(p for p in parts if p != "")

    def _block(self, node: SyntaxTreeNode) -> str:
        t = node.type
        if t == "heading":
            level = int(node.tag[1])
            open_tag, close_tag = HEADINGS.get(level, ("[b]", "[/b]"))
            return f"{open_tag}{self._inline(node)}{close_tag}"
        if t == "paragraph":
            return self._inline(node)
        if t == "blockquote":
            return f"[quote]{self._blocks(node.children)}[/quote]"
        if t == "spoiler":
            return f"{SPOILER[0]}{self._blocks(node.children)}{SPOILER[1]}"
        if t == "bullet_list":
            return self._list(node, ordered=False)
        if t == "ordered_list":
            return self._list(node, ordered=True)
        if t in ("fence", "code_block"):
            return f"[code]\n{node.content.rstrip(chr(10))}\n[/code]"
        if t == "hr":
            return HORIZONTAL_RULE
        if t == "table":
            return self._table(node)
        if t == "html_block":
            # Rewrite centred <div>s; pass any other raw HTML through untouched.
            return self._rewrite_divs(node.content).rstrip("\n")
        # Unknown block: fall back to its rendered children so nothing is lost.
        return self._blocks(node.children)

    def _list(self, node: SyntaxTreeNode, ordered: bool) -> str:
        open_tag = "[list=1]" if ordered else "[list]"
        items = "\n".join(self._list_item(item) for item in node.children)
        return f"{open_tag}\n{items}\n[/list]"

    def _list_item(self, item: SyntaxTreeNode) -> str:
        segments: list[str] = []
        for child in item.children:
            rendered = self._block(child)
            if child.type in LIST_TYPES:
                # Nested list: drop onto its own lines beneath the item text.
                segments.append("\n" + rendered)
            elif segments and not segments[-1].endswith("\n"):
                segments.append(" " + rendered)  # loose item: join paragraphs
            else:
                segments.append(rendered)
        return "[*] " + "".join(segments)

    def _table(self, node: SyntaxTreeNode) -> str:
        # Nexus has no table BBCode, so render an aligned monospace grid inside
        # [code] - readable and stable on the page.
        rows: list[list[str]] = []
        for section in node.children:  # thead / tbody
            for tr in section.children:
                rows.append([self._plain(cell).strip() for cell in tr.children])
        if not rows:
            return ""
        widths = [0] * max(len(r) for r in rows)
        for r in rows:
            for i, cell in enumerate(r):
                widths[i] = max(widths[i], len(cell))
        lines = [
            "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(r)).rstrip()
            for r in rows
        ]
        return "[code]\n" + "\n".join(lines) + "\n[/code]"

    # -- inline level -------------------------------------------------------
    def _inline(self, node: SyntaxTreeNode) -> str:
        """Render a block's inline content (its lone 'inline' child)."""
        return "".join(self._inline_node(c) for c in node.children)

    def _inline_node(self, node: SyntaxTreeNode) -> str:
        t = node.type
        if t == "inline":
            return "".join(self._inline_node(c) for c in node.children)
        if t == "text":
            return node.content
        if t == "strong":
            return f"[b]{self._children(node)}[/b]"
        if t == "em":
            return f"[i]{self._children(node)}[/i]"
        if t == "s":
            return f"[s]{self._children(node)}[/s]"
        if t == "link":
            href = node.attrs.get("href", "")
            return f"[url={href}]{self._children(node)}[/url]"
        if t == "image":
            return f"[img]{node.attrs.get('src', '')}[/img]"
        if t == "code_inline":
            return f"{INLINE_CODE[0]}{node.content}{INLINE_CODE[1]}"
        if t == "softbreak":
            # A hard-wrapped source line is one logical line to Nexus (which
            # turns every newline into <br>), so collapse it to a space.
            return " "
        if t == "hardbreak":
            return "\n"
        if t == "html_inline":
            return self._rewrite_divs(node.content)
        return self._children(node)

    def _children(self, node: SyntaxTreeNode) -> str:
        return "".join(self._inline_node(c) for c in node.children)

    def _plain(self, node: SyntaxTreeNode) -> str:
        """Formatting-stripped text, used for table-cell width alignment."""
        if node.type in ("text", "code_inline"):
            return node.content
        if node.type == "softbreak":
            return " "
        if not node.children:
            return node.content or ""
        return "".join(self._plain(c) for c in node.children)

    def _rewrite_divs(self, html: str) -> str:
        """Map <div align="center|left|right"> / </div> onto alignment tags.

        A shared stack pairs each </div> with its opening tag across the whole
        document (the open and close usually arrive as separate html_block
        nodes), so a </div> becomes [/center], [/left] or [/right] only when it
        closes an aligned div; other <div>s keep their raw tags.
        """
        out: list[str] = []
        pos = 0
        for m in DIV_TAG_RE.finditer(html):
            out.append(html[pos : m.start()])
            tag = m.group(0)
            if tag[1] == "/":  # closing </div>
                close = self._div_stack.pop() if self._div_stack else None
                out.append(close if close else tag)
            else:  # opening <div ...>
                align = DIV_ALIGN_RE.search(tag)
                pair = ALIGN_TAGS.get(align.group(1).lower()) if align else None
                self._div_stack.append(pair[1] if pair else None)
                out.append(pair[0] if pair else tag)
            pos = m.end()
        out.append(html[pos:])
        return "".join(out)


def spoiler_plugin(md: MarkdownIt) -> None:
    """Teach markdown-it a ``>!``-prefixed block that becomes ``[spoiler]``.

    The marker mirrors the blockquote ``>`` but with a trailing ``!``, so a
    run of consecutive lines like::

        >! Here be dragons.
        >! (Still the same spoiler.)

    renders as one ``[spoiler]...[/spoiler]`` block. The inner text is handed
    straight back to the block tokenizer, so emphasis, links, lists and even
    nested spoilers inside a spoiler round-trip like markdown anywhere else.
    An unmarked blank line ends the block; a bare ``>!`` line is kept as an
    inner blank line (letting one spoiler hold several paragraphs).

    Must run *before* the blockquote rule, which would otherwise claim the
    leading ``>`` for itself.
    """

    def spoiler(state, start_line: int, end_line: int, silent: bool) -> bool:
        begin = state.bMarks[start_line] + state.tShift[start_line]
        if state.src[begin : begin + 2] != ">!":
            return False
        if silent:  # validation-only pass: report the match, emit nothing
            return True

        # Find where the contiguous run of '>!' lines ends.
        next_line = start_line
        while next_line < end_line:
            if state.isEmpty(next_line):
                break
            pos = state.bMarks[next_line] + state.tShift[next_line]
            if state.src[pos : pos + 2] != ">!":
                break
            next_line += 1

        # Strip '>!' (plus one optional space) off each line so the inner
        # tokenizer sees clean markdown. Remember the originals: bMarks and
        # friends are shared across the whole parse and must be restored.
        saved = []
        for line in range(start_line, next_line):
            pos = state.bMarks[line] + state.tShift[line]
            content = pos + 2
            if content < state.eMarks[line] and state.src[content] == " ":
                content += 1
            saved.append((state.bMarks[line], state.tShift[line], state.sCount[line]))
            state.bMarks[line] = content
            state.tShift[line] = 0
            state.sCount[line] = 0

        token = state.push("spoiler_open", "", 1)
        token.markup = ">!"
        token.map = [start_line, next_line]

        old_parent, old_line_max = state.parentType, state.lineMax
        state.parentType = "spoiler"
        state.lineMax = next_line  # keep paragraphs from spilling past the block
        state.md.block.tokenize(state, start_line, next_line)
        state.parentType, state.lineMax = old_parent, old_line_max

        token = state.push("spoiler_close", "", -1)
        token.markup = ">!"

        for line, marks in zip(range(start_line, next_line), saved):
            state.bMarks[line], state.tShift[line], state.sCount[line] = marks

        state.line = next_line
        return True

    # `alt` lists the block contexts a spoiler may interrupt, so one placed
    # directly under a paragraph (no blank line between) ends that paragraph
    # instead of being swallowed as a lazy continuation line.
    md.block.ruler.before(
        "blockquote",
        "spoiler",
        spoiler,
        {"alt": ["paragraph", "reference", "blockquote", "list"]},
    )


def convert(markdown: str) -> str:
    md = MarkdownIt("commonmark", {"html": True})
    for rule in ("table", "strikethrough"):
        try:
            md.enable(rule)
        except ValueError:
            pass  # rule name changed upstream - degrade gracefully
    spoiler_plugin(md)
    tree = SyntaxTreeNode(md.parse(markdown))
    bbcode = BBCodeRenderer().render(tree)
    # Collapse any run of 3+ blank lines the walk might leave behind.
    return re.sub(r"\n{3,}", "\n\n", bbcode).strip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert a Markdown file to Nexus-flavoured BBCode."
    )
    parser.add_argument(
        "source",
        nargs="?",
        default="README.md",
        help="Markdown file to convert (default: README.md)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output file (default: dist/<source-stem>-nexus.bbcode)",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Write to stdout instead of a file",
    )
    args = parser.parse_args(argv)

    source = Path(args.source)
    if not source.is_file():
        print(f"error: source not found: {source}", file=sys.stderr)
        return 1

    bbcode = convert(source.read_text(encoding="utf-8"))

    if args.stdout:
        sys.stdout.write(bbcode)
        return 0

    out = Path(args.output) if args.output else Path("dist") / f"{source.stem}-nexus.bbcode"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(bbcode, encoding="utf-8")
    print(f"Wrote {out}  ({len(bbcode)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
