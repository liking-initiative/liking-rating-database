from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen

font = TTFont("Nunito-ExtraBold.ttf")
upm = font["head"].unitsPerEm
cmap = font.getBestCmap()
glyphs = font.getGlyphSet()
hmtx = font["hmtx"]

def text_path(text, size, x, y, anchor="start", spacing=0.0, fill="#0b3c74"):
    s = size / upm
    names = [cmap[ord(c)] for c in text]
    width = sum(hmtx[n][0] * s for n in names) + spacing * (len(names) - 1)
    if anchor == "middle": x -= width / 2
    elif anchor == "end": x -= width
    parts = []
    pen_x = x
    for n in names:
        pen = SVGPathPen(glyphs)
        glyphs[n].draw(pen)
        d = pen.getCommands()
        if d:
            parts.append(f'<path transform="translate({pen_x:.2f},{y}) scale({s:.5f},{-s:.5f})" d="{d}"></path>')
        pen_x += hmtx[n][0] * s + spacing
    return f'<g fill="{fill}">' + "".join(parts) + "</g>"

orange = '''<g transform="translate(220,195)" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="0" cy="0" r="70" fill="#f28c28" stroke="#1f1f1f" stroke-width="5"/>
    <ellipse cx="-40" cy="-6" rx="7" ry="20" fill="#ffb066" transform="rotate(-14 -40 -6)"/>
    <circle cx="-42" cy="26" r="5" fill="#ffb066"/>
    <g fill="none" stroke="#1f1f1f" stroke-width="2.5">
      <path d="M0,-50 C-14,-44 -24,-38 -34,-26"/>
      <path d="M0,-50 C-4,-40 -6,-30 -8,-20"/>
      <path d="M0,-50 C10,-42 16,-34 22,-24"/>
      <path d="M0,-50 C20,-46 30,-44 44,-38"/>
      <path d="M0,-50 C-22,-53 -34,-51 -46,-44"/>
    </g>
    <path d="M-6,-52 L-6,-74 C-6,-79 6,-79 6,-74 L6,-52 Z" fill="#5aa832" stroke="#1f1f1f" stroke-width="4"/>
    <path d="M4,-66 C24,-92 52,-90 70,-82 C54,-68 30,-60 4,-66 Z" fill="#4caf50" stroke="#1f1f1f" stroke-width="4"/>
    <g fill="none" stroke="#2e7d32" stroke-width="2">
      <path d="M8,-68 C28,-76 48,-80 64,-80"/>
      <path d="M24,-74 L28,-84"/>
      <path d="M38,-77 L44,-87"/>
      <path d="M24,-74 L22,-66"/>
      <path d="M38,-77 L38,-68"/>
    </g>
    <ellipse cx="0" cy="-76" rx="7" ry="3" fill="#7cc24a" stroke="#1f1f1f" stroke-width="3"/>
  </g>'''

scale = '''<line x1="130" y1="300" x2="310" y2="300" stroke="#0b3c74" stroke-opacity="0.25" stroke-width="6" stroke-linecap="round"/>
  <line x1="130" y1="300" x2="274" y2="300" stroke="#E78A00" stroke-width="6" stroke-linecap="round"/>
  <g stroke="#0b3c74" stroke-opacity="0.55" stroke-width="2">
    <line x1="130" y1="292" x2="130" y2="308"/><line x1="166" y1="294" x2="166" y2="306"/>
    <line x1="202" y1="294" x2="202" y2="306"/><line x1="238" y1="294" x2="238" y2="306"/>
    <line x1="274" y1="294" x2="274" y2="306"/><line x1="310" y1="292" x2="310" y2="308"/>
  </g>
  <circle cx="274" cy="300" r="12" fill="#E78A00" stroke="#0b3c74" stroke-width="3"/>'''

labels = ('<g fill-opacity="0.85">' + text_path("DISLIKE", 11, 130, 326, "start", 1)
          + text_path("LIKE", 11, 310, 326, "end", 1) + "</g>")
name = text_path("likingInitiative", 26, 220, 368, "middle")

hexagon = '<polygon points="220,50 393.2,150 393.2,350 220,450 46.8,350 46.8,150" fill="#fdf3e0" stroke="#E78A00" stroke-width="12" stroke-linejoin="round"/>'

def svg(viewbox, w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewbox}" width="{w}" height="{h}">\n'
            f'  <title>likingInitiative</title>\n  {body}\n</svg>\n')

body = "\n  ".join([hexagon, orange, scale, labels, name])
open("likingInitiative-hex.svg", "w").write(svg("40 44 360 412", 360, 412, body))
open("likingInitiative-avatar.svg", "w").write(svg("0 30 440 440", 440, 440, body))
print("ok")
