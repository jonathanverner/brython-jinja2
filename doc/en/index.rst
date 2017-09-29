:orphan:

.. _features:

Brython Jinja2
================


The ``pytest`` framework makes it easy to write small tests, yet
scales to support complex functional testing for applications and libraries.

An example of a simple test:

.. code-block:: python

    # content of test_sample.py
    def inc(x):
        return x + 1

    def test_answer():
        assert inc(3) == 5


To execute it::

    $ pytest
    ======= test session starts ========
    platform linux -- Python 3.x.y, pytest-3.x.y, py-1.x.y, pluggy-0.x.y
    rootdir: $REGENDOC_TMPDIR, inifile:
    collected 1 item

    test_sample.py F

    ======= FAILURES ========
    _______ test_answer ________

        def test_answer():
    >       assert inc(3) == 5
    E       assert 4 == 5
    E        +  where 4 = inc(3)

    test_sample.py:5: AssertionError
    ======= 1 failed in 0.12 seconds ========

Due to ``pytest``'s detailed assertion introspection, only plain ``assert`` statements are used.


Features
--------

- Python2.6+, Python3.3+, PyPy-2.3, Jython-2.5 (untested);

- Rich plugin architecture, with over 315+ `external plugins <http://plugincompat.herokuapp.com>`_ and thriving community;


Documentation
-------------

Please see :ref:`Contents <toc>` for full documentation, including installation, tutorials and PDF documents.


Bugs/Requests
-------------

Please use the `GitLab issue tracker <https://gitlab.com/Verner/brython-jinja2/issues>`_ to submit bugs or request features.


Changelog
---------

Consult the :ref:`Changelog <changelog>` page for fixes and enhancements of each version.


License
-------

Copyright Jonathan L. Verner, 2017.

Distributed under the terms of the `BSD`_ license, pytest is free and open source software.

.. _`BSD`: https://gitlab.com/Verner/brython-jinja2/LICENSE
