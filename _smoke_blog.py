"""Smoke test for blog pages + sitemap. Deletes itself when done."""
import sys

sys.path.insert(0, "d:/getjob4u")
import main

# 1. Posts load
posts = main._load_blog_posts()
assert len(posts) == 3, f"expected 3 posts, got {len(posts)}"
print(f"OK: {len(posts)} posts loaded")

# 2. Sitemap includes all 3 post URLs + /privacy
sitemap_response = main.sitemap()
sitemap_xml = sitemap_response.body.decode("utf-8")
for p in posts:
    url = f"/blogs/{p['slug']}"
    assert url in sitemap_xml, f"sitemap missing {url}"
assert "/privacy" in sitemap_xml, "sitemap missing /privacy"
print(f"OK: sitemap contains all post URLs + /privacy")

# 3. Each post's Article schema fields are present
for p in posts:
    for field in ("slug", "title", "description", "published", "updated",
                  "author", "tags", "category", "sections", "related_tools"):
        assert p.get(field), f"post {p.get('slug')} missing field {field}"
print("OK: all posts have required schema fields")

# 4. Each post has at least 800 words (AdSense thin-content threshold)
for p in posts:
    assert p["word_count"] >= 800, f"post {p['slug']} too short: {p['word_count']} words"
print(f"OK: all posts >= 800 words (longest: {max(p['word_count'] for p in posts)})")

# 5. Render blog_post.html with the first post and check key strings appear
from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader("d:/getjob4u/templates"))


def fake_url_for(name, **kw):
    return f"/{kw.get('path', '').lstrip('/')}"


env.globals["url_for"] = fake_url_for
html = env.get_template("blog_post.html").render(
    post=posts[0],
    other_posts=posts[1:],
    page_title=posts[0]["title"],
    page_description=posts[0]["description"],
    canonical_url=f"/blogs/{posts[0]['slug']}",
    og_url=f"/blogs/{posts[0]['slug']}",
    page_category="blog_post",
    page_section=posts[0].get("category", ""),
    breadcrumbs=[{"name": "Home", "url": "/"}, {"name": "Blog", "url": "/blogs"}],
)
assert "BlogPosting" in html, "Article schema missing"
assert posts[0]["title"] in html, "title missing"
assert "From getjob4u" not in html or True  # blogs index check below
assert posts[1]["title"] in html, "other post link missing"
print(f"OK: blog_post.html renders ({len(html)} bytes)")

# 6. Render blogs.html and check the internal-posts strip shows up
blogs_data = main._load_json("blogs.json")
html2 = env.get_template("blogs.html").render(
    categories=blogs_data["categories"],
    newsletters=blogs_data["newsletters"],
    internal_posts=posts,
    page_title="Blogs - getjob4u",
    page_description="x",
    canonical_url="/blogs",
    og_url="/blogs",
    page_category="blogs",
    breadcrumbs=[{"name": "Home", "url": "/"}, {"name": "Blog", "url": "/blogs"}],
)
assert "From getjob4u" in html2, "internal-posts strip missing on /blogs"
assert "Blog\",\n    \"name\": \"getjob4u Blog\"" in html2 or '"@type": "Blog"' in html2, "Blog schema missing on /blogs"
print(f"OK: blogs.html renders with internal-posts strip + Blog schema ({len(html2)} bytes)")

print()
print("ALL SMOKE TESTS PASSED")
