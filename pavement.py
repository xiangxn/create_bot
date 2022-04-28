# [[[section imports]]]
import os
import sys
import imp
from paver.easy import *
from paver.setuputils import setup, find_packages
# [[[endsection]]]

sys.path.insert(0, os.path.abspath('.'))

CODE_DIRECTORY = 'create_account'
TESTS_DIRECTORY = 'tests'
PYTEST_FLAGS = ['--doctest-modules']

metadata = imp.load_source('metadata', os.path.join(CODE_DIRECTORY, 'metadata.py'))


def read(filename):
    with open(os.path.join(os.path.dirname(__file__), filename)) as f:
        return f.read()


# [[[section setup]]]
setup(name=metadata.package,
      version=metadata.version,
      author=metadata.authors[0],
      author_email=metadata.emails[0],
      maintainer=metadata.authors[0],
      maintainer_email=metadata.emails[0],
      url=metadata.url,
      include_package_data=True,
      description=metadata.description,
      long_description=read('README.md'),
      packages=find_packages(exclude=(TESTS_DIRECTORY, )),
      install_requires=[],
      zip_safe=False,
      entry_points={'console_scripts': [CODE_DIRECTORY + '= ' + CODE_DIRECTORY + '.main:entry_point']})
# [[[endsection]]]

# [[[section sphinx]]]
options(sphinx=Bunch(builddir="_build"))
# [[[endsection]]]

# [[[section deployoptions]]]
options(deploy=Bunch(htmldir=path(CODE_DIRECTORY + '/docs'), hosts=['host1.hostymost.com', 'host2.hostymost.com'], hostpath='sites/' + CODE_DIRECTORY))
# [[[endsection]]]

# [[[section minilib]]]
options(minilib=Bunch(extra_files=["doctools"], versioned_name=False))
# [[[endsection]]]


# [[[section sdist]]]
@task
@needs('generate_setup', 'minilib', 'setuptools.command.sdist')
def sdist():
    """Overrides sdist to make sure that our setup.py is generated."""
    pass


# [[[endsection]]]


# [[[section html]]]
@task
@needs('paver.doctools.html')
def html(options):
    """Build the docs and put them into our package."""
    destdir = path(CODE_DIRECTORY + '/docs')
    destdir.rmtree()
    # [[[section builtdocs]]]
    builtdocs = path("docs") / options.builddir / "html"
    # [[[endsection]]]
    builtdocs.move(destdir)


# [[[endsection]]]


# [[[section deploy]]]
@task
@cmdopts([('username=', 'u', 'Username to use when logging in to the servers'), ('hostpath=', 'p', 'hostpath to use when directory on the server')])
def deploy(options):
    """Deploy the HTML to the server."""
    for host in options.hosts:
        sh("rsync -avz -e ssh %s/ %s@%s:%s/" % (options.htmldir, options.username, host, options.hostpath))


# [[[endsection]]]


# [[[section clean]]]
@task
def clean(options):
    """Clean (delete) the built files."""
    destdir = path(CODE_DIRECTORY + '/docs')
    destdir.rmtree()
    destdir = path(CODE_DIRECTORY + '.egg-info')
    destdir.rmtree()
    destdir = path('dist')
    destdir.rmtree()
    destdir = path(TESTS_DIRECTORY + '/__pycache__')
    destdir.rmtree()
    destdir = path(CODE_DIRECTORY + '/__pycache__')
    destdir.rmtree()
    destdir = path(CODE_DIRECTORY + '/database/__pycache__')
    destdir.rmtree()
    destdir = path('docs/' + options.builddir)
    destdir.rmtree()
    destdir = path('docs/api')
    destdir.rmtree()
    path('paver-minilib.zip').remove()
    path('setup.py').remove()
    os.system("rm -rf logs/*.log")
    os.system("rm -rf logs/*.log.*")


# [[[endsection]]]


# [[[section run]]]
@task
@consume_args
def run(args):
    """Run the package's main script. All arguments are passed to it."""
    from create_account.main import main
    raise SystemExit(main([CODE_DIRECTORY] + args))


# [[[endsection]]]

# the pass that follows is to work around a weird bug. It looks like
# you can't compile a Python module that ends in a comment.
pass
