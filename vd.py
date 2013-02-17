#!/usr/bin/env python

import jinja2
import logging
import os
import re
import subprocess
import urlparse
from flask import Flask, make_response, redirect, render_template, send_from_directory, url_for
app = Flask(import_name=__name__, static_folder='s')


###
# Create a static() handler for templates.
# This serves static content from either:
#   /s/ or CloudFront
###
def static(path):
    root = app.config.get('STATIC_ROOT', None)
    if root is None:  # Just use /s/ instead of CDN
        return url_for('static', filename=path)
    return urlparse.urljoin(root, path)


@app.context_processor
def inject_static():
    return dict(static=static)


#################################
# Blocks for URL Control
#################################

######
# *** Static-ish Pages
######

@app.route("/index.html")
def redirect_index():
    return redirect('/', code=302)


@app.route("/")
def page_index():
    return render_template('landing.html', target="America", shortcode="")


######
# *** Magic per-state / city / group-targeted URLs
######

# TODO: + US Territories?
# This is needed for some Google Flu Trends and other shortcuts.
states = {'alabama':'AL', 'alaska':'AK', 'arizona':'AZ', 'arkansas':'AR', 'california':'CA', 'colorado':'CO',
          'connecticut':'CT', 'washington-dc':'DC', 'delaware':'DE', 'florida':'FL', 'georgia':'GA', 'hawaii':'HI',
          'idaho':'ID', 'illinois':'IL', 'indiana':'IN', 'iowa':'IA', 'kansas':'KS', 'kentucky':'KT', 'louisiana':'LA',
          'maine':'ME', 'maryland':'MD', 'massachusetts':'MA', 'michigan':'MI', 'minnesota':'MN', 'mississippi':'MS',
          'missouri':'MO', 'montana':'MT', 'nebraska':'NE', 'nevada':'NV', 'new-hampshire':'NH', 'new-jersey':'NJ',
          'new-mexico':'NM', 'new-york':'NY', 'north-carolina':'NC', 'north-dakota':'ND', 'ohio':'OH', 'oklahoma':'OK',
          'oregon':'OR', 'pennsylvania':'PA', 'rhode-island':'RI', 'south-carolina':'SC', 'south-dakota':'SD',
          'tennessee':'TN', 'texas':'TX', 'utah':'UT', 'vermont':'VT', 'virginia':'VA', 'washington':'WA',
          'west-virginia':'WV', 'wisconsin':'WI', 'wyoming':'WY'}

groups = ['moms', 'dads', 'parents', 'patients']

targets = states.keys() + groups

@app.route("/<target>/")
def localized_branding(target):
    if target in groups:
        # Targeting a specific group (moms, etc.)
        return render_template('_base.html', target=target.replace('-', ' ').title(), shortcode="")
    else:
        # Targeting a State
        return render_template('_base.html', target=target.replace('-', ' ').title(), shortcode=states[target])


######
# *** Odd URLs and support functions
######

# Return favicon from the root path
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 's'),
                               'favicon.ico', mimetype='image/x-icon')

# Return robots from the root path
@app.route('/robots.txt')
def robots():
    return send_from_directory(os.path.join(app.root_path, 's'),
                               'robots.txt', mimetype='text/plain')

# Sitemap, since we're hard to index.
@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory(os.path.join(app.root_path, 's'),
                               'sitemap.xml', mimetype='application/xml')

#@app.route('/openid')
#def openid():
#    return send_from_directory(os.path.join(app.root_path, 's'),
#                               'openid', mimetype='application/xrds+xml')

#@app.route('/.well-known/host-meta')
#def host_meta():
#    return send_from_directory(os.path.join(app.root_path, 's'),
#                               'host-meta', mimetype='text/plain')


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5005, debug=True)
else:
    # We're probably being Frozen. Cool.
    app.config['FREEZER_DESTINATION'] = './vd_frozen/'

    app.config['prod'] = True
    # We don't really support SSL given Cloudfront, but ...
    app.config['STATIC_ROOT'] = '//d2ob8jnie7eh8t.cloudfront.net/s/'
