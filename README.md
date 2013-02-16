# Vaccinate Your Doctors

This repository backs the [Vaccinate Doctors Initiative](http://www.VaccinateDoctors.org) and localized campaigns (a [Flask](http://flask.pocoo.org/) app).

This initiatve is a side-project of [ClinDesk](http://www.clindesk.org/) and [White Coat Academy](http://www.whitecoatacademy.org/).

## Overview

This site is frozen via [Frozen-Flask](http://packages.python.org/Frozen-Flask/) then pushed to S3 which backs a CloudFront endpoint.

## Directories

* (Site)/s/
  * Static files. Loaded via CloudFront
* (Site)/templates/
  * [Jinja2](http://jinja.pocoo.org/) templates for Flask.

## Copyright

Some shared libraries are available via an Apache License v2.0 (e.g. BootStrap)

All other work is Copyright 2013, ClinDesk, Inc. Some rights reserved.
