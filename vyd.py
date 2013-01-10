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
    return render_template('index.html')


######
# *** Magic per-state / city / group-targeted URLs
######

# TODO: Add US territories.
states = ['alabama', 'alaska', 'arizona', 'arkansas', 'california', 'colorado', 'connecticut', 'delaware', 'dc',
           'florida', 'georgia', 'hawaii', 'idaho', 'illinois', 'indiana', 'iowa', 'kansas', 'kentucky',
           'louisiana', 'maine', 'maryland', 'massachusetts', 'michigan', 'minnesota', 'mississippi', 'missouri',
           'montana', 'nebraska', 'nevada', 'new-hampshire', 'new-jersey', 'new-mexico', 'new-york', 'north-carolina',
           'north-dakota', 'ohio', 'oklahoma', 'oregon', 'pennsylvania', 'rhode-island',
           'south-carolina', 'south-dakota', 'tennessee', 'texas', 'utah', 'vermont', 'virginia',
           'washington', 'west-virginia', 'wisconsin', 'wyoming']

groups = ['moms', 'dads', 'parents', 'patients']

targets = states + groups

@app.route("/<target>/")
def localized_branding(target):
    if target in groups:
        return render_template('target_group.html')
    else:
        return render_template('target_state.html')


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
    app.config['FREEZER_DESTINATION'] = './vyd_frozen/'

    app.config['prod'] = True
    # We don't really support SSL given Cloudfront, but ...
    app.config['STATIC_ROOT'] = '//d3s13o1hnazzcc.cloudfront.net/s/'
