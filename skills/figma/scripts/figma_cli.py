#!/usr/bin/env python3
"""
Figma CLI Helper for Hermes Agent
Extracts node hierarchy, design tokens, and exports SVG/PNG assets using Figma REST API.
"""

import sys
import os
import json
import urllib.request
import urllib.parse
import re

def parse_figma_url(url_or_key, node_id_arg=None):
    """Extract file_key and node_id from a Figma URL or raw string."""
    if not url_or_key.startswith("http"):
        return url_or_key, node_id_arg

    parsed = urllib.parse.urlparse(url_or_key)
    path_parts = [p for p in parsed.path.split('/') if p]
    
    file_key = None
    if len(path_parts) >= 2 and path_parts[0] in ('file', 'design', 'proto'):
        file_key = path_parts[1]
    elif len(path_parts) == 1:
        file_key = path_parts[0]

    node_id = node_id_arg
    if not node_id:
        query = urllib.parse.parse_qs(parsed.query)
        if 'node-id' in query:
            node_id = query['node-id'][0].replace('-', ':')

    return file_key, node_id

def figma_api_request(endpoint, token):
    """Make GET request to Figma REST API."""
    url = f"https://api.figma.com/v1/{endpoint}"
    req = urllib.request.Request(url, headers={"X-Figma-Token": token})
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(f"Figma API Error ({e.code}): {e.reason}", file=sys.stderr)
        sys.exit(1)

def color_to_hex(color, opacity=1.0):
    """Convert Figma color dict {r, g, b, a} to HEX / RGBA."""
    r = int(color.get('r', 0) * 255)
    g = int(color.get('g', 0) * 255)
    b = int(color.get('b', 0) * 255)
    a = color.get('a', 1.0) * opacity
    if a >= 0.99:
        return f"#{r:02x}{g:02x}{b:02x}"
    return f"rgba({r}, {g}, {b}, {a:.2f})"

def simplify_node(node):
    """Extract key properties for HTML/Tailwind code generation."""
    node_type = node.get('type')
    name = node.get('name')
    node_id = node.get('id')

    res = {
        'id': node_id,
        'name': name,
        'type': node_type,
        'visible': node.get('visible', True),
    }

    # Bounding box
    bbox = node.get('absoluteBoundingBox')
    if bbox:
        res['width'] = round(bbox.get('width', 0), 2)
        res['height'] = round(bbox.get('height', 0), 2)

    # Auto Layout & Spacing
    if 'layoutMode' in node:
        res['layout'] = {
            'mode': node.get('layoutMode'), # HORIZONTAL / VERTICAL
            'primaryAlign': node.get('primaryAxisAlignItems'), # MIN, CENTER, MAX, SPACE_BETWEEN
            'counterAlign': node.get('counterAxisAlignItems'), # MIN, CENTER, MAX, BASELINE
            'itemSpacing': node.get('itemSpacing', 0),
            'padding': {
                'top': node.get('paddingTop', 0),
                'right': node.get('paddingRight', 0),
                'bottom': node.get('paddingBottom', 0),
                'left': node.get('paddingLeft', 0),
            }
        }

    # Style & Appearance
    fills = node.get('fills', [])
    if fills:
        bg_colors = []
        for f in fills:
            if f.get('visible', True) and f.get('type') == 'SOLID':
                bg_colors.append(color_to_hex(f.get('color', {}), f.get('opacity', 1.0)))
        if bg_colors:
            res['fills'] = bg_colors

    strokes = node.get('strokes', [])
    if strokes:
        border_colors = []
        for s in strokes:
            if s.get('visible', True) and s.get('type') == 'SOLID':
                border_colors.append(color_to_hex(s.get('color', {}), s.get('opacity', 1.0)))
        if border_colors:
            res['strokes'] = border_colors
            res['strokeWeight'] = node.get('strokeWeight', 1)

    if 'cornerRadius' in node:
        res['cornerRadius'] = node.get('cornerRadius')

    # Text Node Properties
    if node_type == 'TEXT':
        res['characters'] = node.get('characters', '')
        style = node.get('style', {})
        res['font'] = {
            'family': style.get('fontFamily'),
            'weight': style.get('fontWeight'),
            'size': style.get('fontSize'),
            'lineHeightPx': style.get('lineHeightPx'),
            'letterSpacing': style.get('letterSpacing'),
            'textAlign': style.get('textAlignHorizontal'),
        }

    # Children recursively
    children = node.get('children', [])
    if children:
        res['children'] = [simplify_node(c) for c in children if c.get('visible', True)]

    return res

def main():
    if len(sys.argv) < 2:
        print("Usage: figma_cli.py <figma-url-or-key> [node-id] [output-json]", file=sys.stderr)
        print("Env FIGMA_ACCESS_TOKEN must be set.", file=sys.stderr)
        sys.exit(1)

    token = os.environ.get("FIGMA_ACCESS_TOKEN") or os.environ.get("FIGMA_TOKEN")
    if not token:
        print("Error: FIGMA_ACCESS_TOKEN environment variable is missing.", file=sys.stderr)
        sys.exit(1)

    url_or_key = sys.argv[1]
    node_id_param = sys.argv[2] if len(sys.argv) > 2 else None
    out_file = sys.argv[3] if len(sys.argv) > 3 else None

    file_key, node_id = parse_figma_url(url_or_key, node_id_param)

    print(f"Fetching Figma file: {file_key}, node_id: {node_id or 'FULL DOCUMENT'}...")

    if node_id:
        data = figma_api_request(f"files/{file_key}/nodes?ids={node_id}", token)
        nodes_dict = data.get('nodes', {})
        node_data = nodes_dict.get(node_id, {}).get('document')
        if not node_data:
            print(f"Error: Node {node_id} not found in response.", file=sys.stderr)
            sys.exit(1)
        simplified = simplify_node(node_data)
    else:
        data = figma_api_request(f"files/{file_key}", token)
        doc = data.get('document', {})
        simplified = simplify_node(doc)

    out_json = json.dumps(simplified, indent=2, ensure_ascii=False)
    if out_file:
        with open(out_file, 'w', encoding='utf-8') as f:
            f.write(out_json)
        print(f"Saved extracted structure to {out_file}")
    else:
        print(out_json)

if __name__ == '__main__':
    main()
