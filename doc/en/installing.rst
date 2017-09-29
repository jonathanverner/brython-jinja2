Installation
===============

Dependencies
----------------------------------------


**Pythons**: Brython 3.3.4

**Platforms**: Chrome/Firefox

**PyPI package name**: `brython_jinja2 <http://pypi.python.org/pypi/brython_jinja2>`_

**dependencies**: `brython <http://pypi.python.org/pypi/brython>`_

**documentation as PDF**: `download latest <https://media.readthedocs.org/pdf/brython_jinja2/latest/brython_jinja2.pdf>`_

.. _installation:


Installation::

    pip install brython_jinja2

To check your installation has installed the correct version::

    $ pytest --version
    This is pytest version 3.x.y, imported from $PYTHON_PREFIX/lib/python3.5/site-packages/pytest.py


Our first test run
----------------------------------------------------------

Let's create a first test file with a simple test function::

    # content of test_sample.py
    def func(x):
        return x + 1

    def test_answer():
        assert func(3) == 5

That's it. You can execute the test function now::

