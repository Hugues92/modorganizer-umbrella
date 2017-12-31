import os

import patch

from config import config
from unibuild import Project
from unibuild.modules import b2, sourceforge, Patch, build
from unibuild.projects import python

boost_version = config["boost_version"]
python_version = config["python_version"]
vc_version = config['vc_version_for_boost']

boost_components = [
    "date_time",
    "coroutine",
    "filesystem",
    "thread",
    "log",
    "locale"
]
boost_components_shared = [
    "python"
]

user_config_jam = "user-config-{}.jam".format("64" if config['architecture'] == "x86_64" else "32")

config_template = ("using python\n"
                   "  : {0}\n"
                   "  : {1}/python.exe\n"
                   "  : {2}/Include\n"
                   "  : {1}\n"
                   "  : <address-model>{3}\n"
                   "  : <define>BOOST_ALL_NO_LIB=1\n"
                   "  ;")

boost_path = "{}/boost_{}".format(config["paths"]["build"], config["boost_version"].replace(".", "_"))

def patchboost(context):
    try:
        return True
    except OSError:
        return False

boost_prepare = Project("boost_prepare") \
  .depend(b2.Bootstrap() \
    .depend(Patch.CreateFile(user_config_jam,
                              lambda: config_template.format(
                                    python_version,
                                    os.path.join(python.python['build_path'], "PCBuild",
                                                 "{}".format("" if config['architecture'] == 'x86' else "amd64"))
                                                  .replace("\\",'/'),
                                     os.path.join(python.python['build_path']).replace("\\", '/'),
                                     "64" if config['architecture'] == "x86_64" else "32")
                                 ) \
      .depend(build.Execute(patchboost)
        .depend(sourceforge.Release("boost",
                                    "boost/{0}/boost_{1}.tar.bz2".format(boost_version,boost_version.replace(".", "_")),
                                    tree_depth=1)))))
if config['architecture'] == 'x86_64':
  # This is a convient way to make each boost flavors we build have these dependencies:
  boost_prepare.depend("Python")

boost = Project("boost")
if config['architecture'] == 'x86_64':
  boost_stage = Patch.Copy(os.path.join("{}/stage/lib/boost_python-vc{}-mt-{}-{}.dll"
                                      .format(boost_path,
                                              vc_version.replace(".", ""),
                                              "x64" if config['architecture'] == "x86_64" else "x86",
                                              "_".join(boost_version.split(".")[:-1]))),
                         os.path.join(config["paths"]["install"], "bin"))
  boost.depend(boost_stage)
else:
  boost_stage = boost

with_for_all = ["--with-{0}".format(component) for component in boost_components]
with_for_shared = ["--with-{0}".format(component) for component in boost_components_shared]
commonargs = [
  "address-model={}".format("64" if config['architecture'] == 'x86_64' else "32"),
  "-a",
  "--user-config={}".format(os.path.join(boost_path,user_config_jam)),
  "-j {}".format(config['num_jobs']),
  "toolset=msvc-" + vc_version
]
if config['architecture'] == 'x86_64':
  b2tasks = [
    ("Shared", ["link=shared"] + with_for_all + with_for_shared),
    ("Static", ["link=static", "runtime-link=shared"] + with_for_all),
    ("StaticCRT64", ["link=static", "runtime-link=static"] + with_for_all)
  ]
else:
  b2tasks = [
    ("StaticCRT32", ["link=static", "runtime-link=static", "--buildid=x86"] + with_for_all)
  ]
for (taskname, taskargs) in b2tasks:
  boost_stage.depend(b2.B2(taskname,boost_path).arguments(commonargs + taskargs)
    .depend(boost_prepare))
