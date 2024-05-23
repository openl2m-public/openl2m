.. image:: ../_static/openl2m_logo.png

Code Introduction
=================

This document attempts to describe how OpenL2M is functioning inside the Django framework

As of version 2, we have a base API class called Connector(). This class implements
all the functions that are called by the Django application to extract data from and perform actions on a network device.
This class and its derived vendor-specific classes is where all the funs happens! It is implemented in the 'switches' app.
And you will also need to know a little about how we use the Django framework.

:doc:`A graphical overview of the data models used is here. <data_model>`.
This image is created using the 'django-extensions' with the command
'*python3 openl2m/manage.py graph_models -a -o openl2m_models.png*'

**Django**

As is Django custom, all Django files are stored in the *openl2m/* sub-directory.
From here forward, all references to other directories will be relative to this location.

**The OpenL2M Django Project**

A Django project consists of a project definition directory, and one or more applications in separate directories.

Django's "project" is in the *openl2m/* directory. This is where the whole process starts.

* *urls.py*

This file is the 'mapper' where all urls paths are mapped, either directly or by
including url files from the apps that make up the project.

* *admin.py*

Here we create a custom admin site variable, named "admin_site".
This allows use to make changes to the admin functionality and views,
and is referenced also in the "users" app. We customize the admin site
`using the techniques described here.
<https://docs.djangoproject.com/en/5.0/ref/contrib/admin/#hooking-adminsite-to-urlconf>`_

**Authentication**

All pages require user authentication. :doc:`This is described here. <authentication>`

**The apps**

There are three apps at this time:

* :doc:`users <users_app/index>`

This where additional attributes are defined for the built-in Django User()
object. It is in the users/ directory.

* :doc:`switches <switches_app/index>`

This is where most of the work of the Web GUI is handled. Also the Connector() class and
its derived device driver classes and code
that handle SNMP, Junos PyEZ, Aruba AOS-CX, Napalm, SSH, etc. are located in the switches/ directory.

* :doc:`counters <counters_app/index>`

This is a simple app that adds a named counter object and functionality. It is used throughout to track some usage counters.

* :doc:`notices <notices_app/index>`

This is a simple app that adds a notification that can be shown during login.


**Additional directories**

They are:

* *templates/*

This is where all templates are stored. (I.e. we use a central directory,
and not templates-per-app, as is custom for some other Django applications)

* *static/*

This is where static files such as CSS, images, etc. are stored.
This is separately mapped in :doc:`the web server config <../installation/index>`.
The content of this folder is created when running the ./upgrade.sh script.

* *static-project/*

This is the base location for all static CSS, images, etc.
This where you maintain these files. The upgrade.sh script copies
files as needed to the *static/* directory.


**Upgrading to new Django versions**

If you need to upgrade to another major.minor Django version, e.g. from 4.2 to 5.0,
at minimum you need to follow the steps in the Django upgrade version documentation

E.g. for v5.0, this can be found at https://docs.djangoproject.com/en/5.0/howto/upgrade-version/

**High-Level overview of Elements:**

.. image:: ../_static/openl2m-architecture.png

