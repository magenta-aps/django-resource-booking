from setuptools import setup, find_packages

version = '1.0'

setup(
    name="django_resource_booking",
    version=version,
    description="Resource booking and allocation for large organizations.",
    long_description="""
Resource booking and allocation for large organizations - specifically
designed for the University of Copenhagen.""",
      classifiers=[],
      keywords='',
      author='Magenta ApS',
      author_email='info@magenta.dk',
      url='http://magenta.dk',
      license='GLPv3',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          # -*- Extra requirements: -*-
          'Django==2.2.17',
          'flake8==3.8.4',
          'psycopg2-binary',
          'django-npm==1.0.0',
          'django-recurrence==1.10.3',
          'django-tinymce==2.8.0',
          'djangosaml2==0.17.2',
          'django-cron==0.5.1',
          'django-ckeditor==5.6.1',
          'django-macros==0.4.0',
          'djorm-ext-pgfulltext==0.10',
          'requests==2.20.0',
          'django-debug-toolbar==1.11',
          'django-hijack==2.1.10',
          'beautifulsoup4==4.7.1',
          'Pillow==9.0.0',
          'django-extensions==2.1.9',
          "pyquery==1.4.1",
          "freezegun==1.0.0",
          "bpython==0.18",
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
