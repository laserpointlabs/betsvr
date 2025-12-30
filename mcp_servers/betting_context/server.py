from mcp.server.fastmcp import FastMCP
import os
from typing import List
import pypdf

# Initialize FastMCP server
mcp = FastMCP("BettingContext")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

def get_file_text(filepath: str) -> str:
    """Extract text from a file (PDF or Markdown)."""
    text = ""
    try:
        if filepath.lower().endswith('.pdf'):
            with open(filepath, 'rb') as file:
                reader = pypdf.PdfReader(file)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
        elif filepath.lower().endswith('.md') or filepath.lower().endswith('.markdown'):
            with open(filepath, 'r', encoding='utf-8') as file:
                text = file.read()
        else:
            return f"Error: Unsupported file format for {os.path.basename(filepath)}"
    except Exception as e:
        return f"Error reading file: {str(e)}"
    return text

@mcp.tool()
def list_guides() -> List[str]:
    """List all available betting guides (PDF and Markdown) in the data folder. Use this to discover what knowledge is available."""
    if not os.path.exists(DATA_DIR):
        return []
    return [f for f in os.listdir(DATA_DIR) if f.lower().endswith(('.pdf', '.md', '.markdown'))]

@mcp.tool()
def read_guide(filename: str) -> str:
    """Read the full content of a specific betting guide (PDF or Markdown). Use this when you need comprehensive information from a specific guide file."""
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        return f"Error: File '{filename}' not found."

    # Security check to prevent directory traversal
    if os.path.commonpath([os.path.abspath(filepath), os.path.abspath(DATA_DIR)]) != os.path.abspath(DATA_DIR):
         return "Error: Access denied."

    return get_file_text(filepath)

@mcp.tool()
def search_guides(query: str) -> str:
    """[EXPERT GUIDES] Search betting strategy guides for concepts, advice, and how-to information. USE THIS for WHY/HOW/WHAT IS/SHOULD I questions about betting theory, not for live game odds."""
    if not os.path.exists(DATA_DIR):
        return "No data directory found."

    # Extract meaningful keywords from query (remove common words)
    stop_words = {'the', 'is', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'what', 'how', 'why', 'when', 'should', 'i', 'my', 'me', 'such', 'are', 'was', 'were', 'be', 'been'}
    query_words = [w.lower() for w in query.split() if w.lower() not in stop_words and len(w) > 2]

    if not query_words:
        query_words = [query.lower()]

    results = []
    files = [f for f in os.listdir(DATA_DIR) if f.lower().endswith(('.pdf', '.md', '.markdown')) and f != 'README.md']

    # Score each section by relevance
    scored_sections = []

    for filename in files:
        text = get_file_text(os.path.join(DATA_DIR, filename))

        # Split by headers
        sections = text.split('\n## ')
        for idx, section in enumerate(sections):
            section_lower = section.lower()

            # Count keyword matches
            matches = sum(1 for word in query_words if word in section_lower)

            if matches > 0:
                # Higher score for more matches
                score = matches

                # Boost score if it's the main section (has ##)
                if idx == 0 and section.startswith('#'):
                    section = section  # Keep as-is
                else:
                    section = '## ' + section  # Restore header

                scored_sections.append((score, filename, section.strip()))

    if not scored_sections:
        # No keyword matches - return guide summaries instead
        summaries = []
        for f in files:
            if 'nfl_betting' in f.lower():
                summaries.append(f"📘 {f}: NFL strategies - key numbers (3,7), QB value, situational spots, weather, line movement, CLV")
            elif 'ncaa' in f.lower():
                summaries.append(f"📘 {f}: College football - recruiting, motivation, high variance, tempo, weather")
            elif 'bankroll' in f.lower():
                summaries.append(f"📘 {f}: Bankroll management - unit sizing, Kelly Criterion, drawdown rules, stop-loss")
            elif 'glossary' in f.lower():
                summaries.append(f"📘 {f}: Terms - CLV, steam, sharp/square, RLM, hedge, middle, teaser")
            elif 'player_props' in f.lower():
                summaries.append(f"📘 {f}: Player props & PrizePicks - QB/RB/WR props, correlations, game script, matchup adjustments")
            elif 'parlay' in f.lower():
                summaries.append(f"📘 {f}: Parlays & Teasers - Wong teasers, SGP strategy, correlation, portfolio allocation")
            elif 'line_shopping' in f.lower():
                summaries.append(f"📘 {f}: Line shopping & Value - CLV tracking, EV calculation, key number value, juice comparison")
            elif 'basics' in f.lower():
                summaries.append(f"📘 {f}: Basics - moneyline, spread, totals explained for beginners")

        return f"No exact matches for '{query}'. Available guides:\n" + "\n".join(summaries) + "\n\nUse read_guide(filename) to read the full guide."

    # Sort by score (highest first) and take top 3 sections
    scored_sections.sort(reverse=True, key=lambda x: x[0])
    top_sections = scored_sections[:3]

    output = f"[EXPERT BETTING GUIDES - Found {len(top_sections)} relevant section(s)]\n\n"
    for score, filename, section in top_sections:
        output += f"--- From {filename} (Relevance: {score}) ---\n{section}\n\n"

    return output

if __name__ == "__main__":
    mcp.run()
