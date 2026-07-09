"""Convert markdown formatting to DOCX run formatting."""

import re
from typing import List, Tuple, Dict, Any
from docx.oxml import OxmlElement
from docx.shared import Pt, RGBColor


class MarkdownFormatter:
    """Parse and apply markdown formatting to DOCX paragraphs."""

    @staticmethod
    def parse_blocks(text: str) -> List[Dict[str, Any]]:
        """Parse markdown into block-level elements.

        Returns list of dicts with 'type' and content:
        - {'type': 'heading', 'level': 1-6, 'text': ...}
        - {'type': 'table', 'rows': [...]}
        - {'type': 'paragraph', 'text': ...}
        - {'type': 'bullet_list', 'items': [...]}
        - {'type': 'numbered_list', 'items': [...]}
        - {'type': 'code_block', 'code': ...}
        """
        blocks = []
        lines = text.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i]

            # Skip empty lines
            if not line.strip():
                i += 1
                continue

            # Check for headers
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if header_match:
                level = len(header_match.group(1))
                text_content = header_match.group(2).strip()
                blocks.append({'type': 'heading', 'level': level, 'text': text_content})
                i += 1
                continue

            # Check for tables
            if line.strip().startswith('|'):
                table_rows = []
                while i < len(lines) and lines[i].strip().startswith('|'):
                    row_text = lines[i].strip()
                    # Parse row: |col1|col2|col3|
                    cells = [cell.strip() for cell in row_text.split('|')[1:-1]]
                    # Skip separator rows (---)
                    if not all(c.replace('-', '').replace(' ', '') == '' for c in cells):
                        table_rows.append(cells)
                    i += 1

                if table_rows:
                    blocks.append({'type': 'table', 'rows': table_rows})
                continue

            # Check for bullet lists
            bullet_match = re.match(r'^[-*]\s+(.+)$', line)
            if bullet_match:
                items = []
                while i < len(lines) and re.match(r'^[-*]\s+(.+)$', lines[i]):
                    match = re.match(r'^[-*]\s+(.+)$', lines[i])
                    items.append(match.group(1))
                    i += 1
                blocks.append({'type': 'bullet_list', 'items': items})
                continue

            # Check for numbered lists
            numbered_match = re.match(r'^\d+\.\s+(.+)$', line)
            if numbered_match:
                items = []
                while i < len(lines) and re.match(r'^\d+\.\s+(.+)$', lines[i]):
                    match = re.match(r'^\d+\.\s+(.+)$', lines[i])
                    items.append(match.group(1))
                    i += 1
                blocks.append({'type': 'numbered_list', 'items': items})
                continue

            # Default: paragraph
            blocks.append({'type': 'paragraph', 'text': line.strip()})
            i += 1

        return blocks

    @staticmethod
    def parse_markdown_text(text: str) -> List[Tuple[str, dict]]:
        """Parse markdown text into runs with formatting.

        Args:
            text: Text with markdown formatting (**, *, etc.)

        Returns:
            List of (text, formatting) tuples
        """
        runs = []
        pos = 0

        # Pattern to find bold (**), italic (*), or bold+italic (***)
        # Matches: **text**, *text*, or ***text***
        pattern = r"\*{1,3}([^*]+?)\*{1,3}|([^*]+)"

        for match in re.finditer(pattern, text):
            if match.group(1):  # Has markdown formatting
                formatted_text = match.group(1)
                asterisks = match.group(0).split(formatted_text)[0]  # Get leading asterisks

                formatting = {}
                if "**" in asterisks or formatted_text in match.group(0) and match.group(0).count("*") >= 4:
                    # Bold or bold+italic
                    formatting["bold"] = True
                if "*" in asterisks.replace("**", ""):
                    # Italic or bold+italic (single * not part of **)
                    formatting["italic"] = True

                # Check for ***text***
                if match.group(0).startswith("***") and match.group(0).endswith("***"):
                    formatting["bold"] = True
                    formatting["italic"] = True
                elif match.group(0).startswith("**") and match.group(0).endswith("**"):
                    formatting["bold"] = True
                elif match.group(0).startswith("*") and match.group(0).endswith("*"):
                    formatting["italic"] = True

                runs.append((formatted_text, formatting))
            else:  # Plain text
                plain_text = match.group(2)
                if plain_text:
                    runs.append((plain_text, {}))

        return runs if runs else [(text, {})]

    @staticmethod
    def apply_formatting(paragraph, text: str) -> None:
        """Apply markdown formatting to a paragraph.

        Args:
            paragraph: python-docx paragraph object
            text: Text with markdown formatting
        """
        # Clear default run
        paragraph.clear()

        # Parse and add formatted runs
        runs_data = MarkdownFormatter.parse_markdown_text(text)

        for run_text, formatting in runs_data:
            run = paragraph.add_run(run_text)

            if formatting.get("bold"):
                run.font.bold = True
            if formatting.get("italic"):
                run.font.italic = True

    @staticmethod
    def simple_parse(text: str) -> List[Tuple[str, dict]]:
        """Simple markdown parser for common cases.

        Handles: **bold**, *italic*, ***bold+italic***

        Args:
            text: Text with markdown

        Returns:
            List of (text, formatting_dict) tuples
        """
        segments = []
        pos = 0

        # Match patterns: ***text***, **text**, *text*
        for match in re.finditer(r"\*\*\*(.+?)\*\*\*|\*\*(.+?)\*\*|\*(.+?)\*", text):
            # Add text before match
            if match.start() > pos:
                segments.append((text[pos:match.start()], {}))

            # Add formatted text
            if match.group(1):  # ***bold+italic***
                segments.append((match.group(1), {"bold": True, "italic": True}))
            elif match.group(2):  # **bold**
                segments.append((match.group(2), {"bold": True}))
            elif match.group(3):  # *italic*
                segments.append((match.group(3), {"italic": True}))

            pos = match.end()

        # Add remaining text
        if pos < len(text):
            segments.append((text[pos:], {}))

        return segments if segments else [(text, {})]
