import datetime
import collections
import html
from pathlib import Path
from typing import List, Dict
from newssummary.models import Article

BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - News Summary</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
    <style>
        :root {{ 
            --pico-font-size: 100%; 
            --pico-border-radius: 12px;
        }}
        
        /* Custom News Grid that actually wraps */
        .news-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}

        .category-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 1rem;
        }}

        article {{ 
            margin-bottom: 0; 
            height: 100%; 
            display: flex; 
            flex-direction: column;
            border-radius: var(--pico-border-radius);
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            transition: transform 0.2s, box-shadow 0.2s;
            border: 1px solid var(--pico-muted-border-color);
        }}
        
        article:hover {{
            transform: translateY(-4px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.12);
        }}

        article footer {{ 
            margin-top: auto; 
            display: flex;
            gap: 0.5rem;
        }}

        /* Trending Story Accents */
        .trending-story {{ border-top: 4px solid var(--pico-primary); }}
        .source-count {{ 
            background: var(--pico-primary); 
            color: white; 
            padding: 2px 8px; 
            border-radius: 12px; 
            font-size: 0.75rem; 
            font-weight: bold;
        }}

        .badge {{ 
            font-size: 0.7rem; 
            padding: 2px 6px; 
            border-radius: 4px; 
            background: var(--pico-secondary-background);
            margin-right: 5px;
            text-transform: uppercase;
            font-weight: bold;
        }}

        .reading-time {{
            font-size: 0.75rem;
            opacity: 0.7;
            display: flex;
            align-items: center;
            gap: 4px;
        }}

        .comparison-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 1.5rem;
        }}

        h1, h2 {{ border-bottom: 2px solid var(--pico-muted-border-color); padding-bottom: 0.5rem; margin-top: 2rem; }}
        .breadcrumb {{ margin-bottom: 2rem; }}
        
        .cat-card {{ padding: 1rem; text-align: center; border: 1px solid var(--pico-muted-border-color); }}

        .copy-btn {{
            font-size: 0.8rem;
            padding: 4px 8px;
            margin: 0;
        }}
    </style>
</head>
<body>
    <header class="container">
        <nav>
            <ul>
                <li><strong><a href="index.html" class="contrast">Daily Intelligence</a></strong></li>
            </ul>
            <ul>
                <li>{date}</li>
            </ul>
        </nav>
    </header>
    <main class="container">
        {content}
    </main>
    <footer class="container">
        <hr>
        <div style="display: flex; justify-content: space-between; opacity: 0.7; font-size: 0.8rem;">
            <span>Generated on {timestamp}</span>
            <span>Local Digest System</span>
        </div>
    </footer>
    <script>
        function copyToClipboard(btn) {{
            const text = btn.getAttribute('data-summary');
            
            // Try modern API first
            if (navigator.clipboard && window.isSecureContext) {{
                navigator.clipboard.writeText(text).then(() => showSuccess(btn));
                return;
            }}

            // Fallback for file:// or older browsers
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.left = '-9999px';
            textarea.style.top = '0';
            document.body.appendChild(textarea);
            textarea.focus();
            textarea.select();
            
            try {{
                const successful = document.execCommand('copy');
                if (successful) showSuccess(btn);
            }} catch (err) {{
                console.error('Fallback copy failed', err);
            }}
            
            document.body.removeChild(textarea);
        }}

        function showSuccess(btn) {{
            const originalText = btn.innerText;
            btn.innerText = 'Copied!';
            btn.classList.remove('outline');
            setTimeout(() => {{
                btn.innerText = originalText;
                btn.classList.add('outline');
            }}, 2000);
        }}
    </script>
</body>
</html>
"""


def generate_digest(
    all_articles: List[Article],
    elevated_topics: List[List[Article]],
    broad_groups: Dict[str, List[Article]],
):
    today = datetime.date.today().isoformat()
    digest_dir = Path("digest") / today
    digest_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Group by source
    source_groups = collections.defaultdict(list)
    for art in all_articles:
        source_groups[art.source_name].append(art)

    # 1. Generate Index Page
    index_content = ""

    if elevated_topics:
        index_content += "<h2>🔥 Top Trending Stories</h2>"
        index_content += '<div class="news-grid">'
        for i, topic in enumerate(elevated_topics):
            main_art = topic[0]
            snippet = (
                main_art.summary[:200] + "..."
                if len(main_art.summary) > 200
                else main_art.summary
            )
            index_content += f"""
            <article class="trending-story">
                <header>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                        <div>
                            <span class="badge">{main_art.language}</span>
                            <span class="reading-time">⏱️ {main_art.reading_time} min read</span>
                        </div>
                        <span class="source-count">{len(topic)} Sources</span>
                    </div>
                    <h3 style="margin:0; font-size: 1.2rem;">{main_art.title}</h3>
                </header>
                <p style="font-size: 0.9rem;">{snippet}</p>
                <footer>
                    <a href="topic_{i}.html" role="button" class="contrast" style="flex: 1;">Deep Dive</a>
                    <button class="outline secondary copy-btn" data-summary="{html.escape(main_art.summary)}" onclick="copyToClipboard(this)">Copy</button>
                </footer>
            </article>
            """
        index_content += "</div>"

    if broad_groups:
        index_content += "<h2>📂 Categories</h2>"
        index_content += '<div class="category-grid">'
        for cat in sorted(broad_groups.keys()):
            count = len(broad_groups[cat])
            slug = cat.lower().replace(" ", "_").replace("&", "n")
            filename = f"category_{slug}.html"
            index_content += f"""
            <a href="{filename}" style="text-decoration: none;">
                <article class="cat-card">
                    <strong>{cat}</strong>
                    <div style="font-size: 0.8rem; opacity: 0.6;">{count} articles</div>
                </article>
            </a>
            """
        index_content += "</div>"

    if source_groups:
        index_content += "<h2>📰 News Sources</h2>"
        index_content += '<div class="category-grid">'
        for source_name in sorted(source_groups.keys()):
            count = len(source_groups[source_name])
            slug = source_name.lower().replace(" ", "_")
            filename = f"source_{slug}.html"
            index_content += f"""
            <a href="{filename}" style="text-decoration: none;">
                <article class="cat-card">
                    <strong>{source_name}</strong>
                    <div style="font-size: 0.8rem; opacity: 0.6;">{count} stories</div>
                </article>
            </a>
            """
        index_content += "</div>"

    index_html = BASE_TEMPLATE.format(
        title="Dashboard", date=today, content=index_content, timestamp=timestamp
    )
    (digest_dir / "index.html").write_text(index_html)

    # 2. Generate Topic Pages
    for i, topic in enumerate(elevated_topics):
        topic_content = f'<nav class="breadcrumb"><ul><li><a href="index.html">Home</a></li><li>Trending Story</li></ul></nav>'
        topic_content += f"<h1>{topic[0].title}</h1>"
        topic_content += '<div class="comparison-grid">'
        for art in topic:
            topic_content += f"""
            <article>
                <header>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                        <div>
                            <span class="badge">{art.language.upper()}</span> 
                            <strong>{art.source_name}</strong>
                        </div>
                        <span class="reading-time">⏱️ {art.reading_time} min read</span>
                    </div>
                    <strong>{art.title}</strong>
                </header>
                <p>{art.summary}</p>
                <footer>
                    <a href="{art.url}" target="_blank" class="secondary outline" style="flex: 1; font-size: 0.8rem;">Original</a>
                    <button class="outline secondary copy-btn" data-summary="{html.escape(art.summary)}" onclick="copyToClipboard(this)">Copy</button>
                </footer>
            </article>
            """
        topic_content += "</div>"
        topic_html = BASE_TEMPLATE.format(
            title=f"Story: {topic[0].title[:40]}",
            date=today,
            content=topic_content,
            timestamp=timestamp,
        )
        (digest_dir / f"topic_{i}.html").write_text(topic_html)

    # 3. Generate Category Pages
    for cat, articles in broad_groups.items():
        cat_slug = cat.lower().replace(" ", "_").replace("&", "n")
        cat_content = f'<nav class="breadcrumb"><ul><li><a href="index.html">Home</a></li><li>{cat}</li></ul></nav>'
        cat_content += f"<h1>{cat} Digest</h1>"
        cat_content += '<div class="news-grid">'
        for art in articles:
            cat_content += f"""
            <article>
                <header>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                        <div>
                            <span class="badge">{art.language.upper()}</span> 
                            <strong>{art.source_name}</strong>
                        </div>
                        <span class="reading-time">⏱️ {art.reading_time} min read</span>
                    </div>
                    <strong>{art.title}</strong>
                </header>
                <p style="font-size: 0.95rem;">{art.summary}</p>
                <footer>
                    <a href="{art.url}" target="_blank" class="contrast outline" style="flex: 1; font-size: 0.8rem;">Original</a>
                    <button class="outline secondary copy-btn" data-summary="{html.escape(art.summary)}" onclick="copyToClipboard(this)">Copy</button>
                </footer>
            </article>
            """
        cat_content += "</div>"
        cat_html = BASE_TEMPLATE.format(
            title=cat, date=today, content=cat_content, timestamp=timestamp
        )
        (digest_dir / f"category_{cat_slug}.html").write_text(cat_html)

    # 4. Generate Source Pages
    for source_name, articles in source_groups.items():
        source_slug = source_name.lower().replace(" ", "_")
        source_content = f'<nav class="breadcrumb"><ul><li><a href="index.html">Home</a></li><li>Sources</li><li>{source_name}</li></ul></nav>'
        source_content += f"<h1>Latest from {source_name}</h1>"
        source_content += '<div class="news-grid">'
        for art in articles:
            source_content += f"""
            <article>
                <header>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                        <span class="badge">{art.category}</span>
                        <span class="reading-time">⏱️ {art.reading_time} min read</span>
                    </div>
                    <strong>{art.title}</strong>
                </header>
                <p style="font-size: 0.95rem;">{art.summary}</p>
                <footer>
                    <a href="{art.url}" target="_blank" class="contrast outline" style="flex: 1; font-size: 0.8rem;">Original</a>
                    <button class="outline secondary copy-btn" data-summary="{html.escape(art.summary)}" onclick="copyToClipboard(this)">Copy</button>
                </footer>
            </article>
            """
        source_content += "</div>"
        source_html = BASE_TEMPLATE.format(
            title=source_name, date=today, content=source_content, timestamp=timestamp
        )
        (digest_dir / f"source_{source_slug}.html").write_text(source_html)

    return digest_dir / "index.html"
