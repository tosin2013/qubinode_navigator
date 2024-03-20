---
# Feel free to add content and custom Front Matter to this file.
# To modify the layout, see https://jekyllrb.com/docs/themes/#overriding-theme-defaults

layout: home
---

# Show post links
{% for post in site.posts %}
  <a href="{{ post.url }}">{{ post.title }}</a>
{% endfor %}