.. image:: https://circleci.com/gh/tprrt/blog.svg?style=svg
    :alt: Circle badge
    :target: https://app.circleci.com/pipelines/github/tprrt/blog

.. image:: https://sonarcloud.io/api/project_badges/measure?project=tprrt_blog&metric=alert_status
    :alt: Quality Gate Status
    :target: https://sonarcloud.io/dashboard?id=tprrt_blog

==============
My static blog
==============

My embedded Linux developer's blog built with Pelican, an static site generator
written in Python. The content of this blog is written in reStructuredText.

License
=======

This repository uses dual licensing:

- **Content & Media** (files in ``content/`` directory including articles and
  images): Licensed under `Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0) <LICENSE-CONTENT>`_
- **Code & Build System** (Pelican configuration, themes, plugins, and build
  scripts): Licensed under `GNU General Public License v3.0 (GPLv3) <LICENSE>`_

Support
=======

If you find this blog useful and would like to support its development, you can
make a donation via PayPal:

https://paypal.me/tprrt

----

Use commands below to install required Python modules to build static pages and to push them on github:

.. code-block:: bash

    # To pull submodules' sources
    git submodule sync
    git submodule update --init
    cd pelican-themes && git submodule update --init --recursive -- blue-penguin && cd -
    cd pelican-plugins && git submodule update --init --recursive -- assets sitemap && cd -

    # To create a Python3 virtual environment
    python3 -m venv venv
    . venv/bin/activate

    # To install required Python modules
    pip install -r requirements.txt

    # To view generated files before to push them, once the simple built-in web
    # service has been started, the site can be preview at:
    # http://http://localhost:8000/
    pelican [-D] content -o output -s pelicanconf.py
    pelican -l content -o output -s pelicanconf.py -p 8000

    # To generate static pages should be published
    pelican [-D] content -o output -s publishconf.py

    # To publish pages to gh-pages
    ghp-import -n output -m "[skip ci] Update pages"
    git push origin gh-pages

    # To quit the Python3 virtual environment
    deactivate


----

Use the following command to validate the `circleci`_ pipeline:

.. code-block:: bash

    podman run --rm --security-opt seccomp=unconfined --security-opt label=disable -v $(pwd):/data circleci/circleci-cli:alpine config validate /data/.circleci/config.yml --token $TOKEN


.. _circleci: https://circleci.com
