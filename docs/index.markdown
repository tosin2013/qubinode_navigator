---
# Feel free to add content and custom Front Matter to this file.
# To modify the layout, see https://jekyllrb.com/docs/themes/#overriding-theme-defaults

layout: home
---

{% for page in site.pages %}
- [{{ page.title }}]({{ page.url | relative_url }})
{% endfor %}