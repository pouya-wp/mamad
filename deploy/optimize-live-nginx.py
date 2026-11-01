"""Apply static asset delivery settings to the Certbot-managed ONE CAFE Nginx site.

Run on the VPS. The TLS directives remain untouched.
"""

from pathlib import Path
import shutil


site = Path('/etc/nginx/sites-available/onecafe')
source = site.read_text()
if 'gzip_vary on;' in source:
    print('Static delivery settings already installed.')
    raise SystemExit(0)

replacements = [
    (
        '    client_max_body_size 20m;\n',
        '    client_max_body_size 20m;\n'
        '    gzip on;\n'
        '    gzip_vary on;\n'
        '    gzip_min_length 1024;\n'
        '    gzip_types text/css application/javascript application/json image/svg+xml;\n',
    ),
    (
        '    location ~ ^/(api|files|private)/ {\n',
        '    location ~ ^/(api|files|private)/ {\n'
        '        gzip off;\n',
    ),
    (
        '    location / {\n',
        '    location /assets/ {\n'
        '        add_header Cache-Control "public, max-age=31536000, immutable";\n'
        '    }\n\n'
        '    location = /index.html {\n'
        '        add_header Cache-Control "no-cache";\n'
        '    }\n\n'
        '    location / {\n',
    ),
]
for old, new in replacements:
    if source.count(old) != 1:
        raise SystemExit(f'Expected exactly one occurrence of {old!r}; site unchanged.')
    source = source.replace(old, new, 1)

shutil.copy2(site, site.with_name(site.name + '.pre-static-speed'))
site.write_text(source)
print('Installed static delivery settings; run nginx -t before reloading.')
