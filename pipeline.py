# -*- coding: utf-8 -*-
import datetime
from distutils.version import StrictVersion
import fcntl
import os
import sys
import pty
from seesaw import item
import seesaw
from seesaw.config import NumberConfigValue
from seesaw.externalprocess import ExternalProcess
from seesaw.item import ItemInterpolation, ItemValue
from seesaw.pipeline import Pipeline
from seesaw.project import Project
from seesaw.task import SimpleTask, LimitConcurrent, ConditionalTask
from seesaw.tracker import GetItemFromTracker, SendDoneToTracker, \
    PrepareStatsForTracker, UploadWithTracker
from seesaw.util import find_executable
import shutil
import subprocess
import time
from tornado.ioloop import IOLoop, PeriodicCallback

# This forces subprocess to allow utf-8 usernames
# http://stackoverflow.com/q/492483
reload(sys)
sys.setdefaultencoding('utf-8')

# check the seesaw version
if StrictVersion(seesaw.__version__) < StrictVersion("0.0.15"):
    raise Exception("This pipeline needs seesaw version 0.0.15 or higher.")

# Begin AsyncPopen fix
class AsyncPopenFixed(seesaw.externalprocess.AsyncPopen):
    """
    Start the wait_callback after setting self.pipe, to prevent an infinite
    spew of "AttributeError: 'AsyncPopen' object has no attribute 'pipe'"
    """
    def run(self):
        self.ioloop = IOLoop.instance()
        (master_fd, slave_fd) = pty.openpty()

        # make stdout, stderr non-blocking
        fcntl.fcntl(master_fd, fcntl.F_SETFL,
            fcntl.fcntl(master_fd, fcntl.F_GETFL) | os.O_NONBLOCK)

        self.master_fd = master_fd
        self.master = os.fdopen(master_fd)

        # listen to stdout, stderr
        self.ioloop.add_handler(master_fd, self._handle_subprocess_stdout,
            self.ioloop.READ)

        slave = os.fdopen(slave_fd)
        self.kwargs["stdout"] = slave
        self.kwargs["stderr"] = slave
        self.kwargs["close_fds"] = True
        self.pipe = subprocess.Popen(*self.args, **self.kwargs)

        self.stdin = self.pipe.stdin

        # check for process exit
        self.wait_callback = PeriodicCallback(self._wait_for_end, 250)
        self.wait_callback.start()

seesaw.externalprocess.AsyncPopen = AsyncPopenFixed
# End AsyncPopen fix




###########################################################################
# The version number of this pipeline definition.
#
# Update this each time you make a non-cosmetic change.
# It will be added to the WARC files and reported to the tracker.
VERSION = "20140210.01"
USER_AGENT = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.101 Safari/537.36"
TRACKER_ID = 'myopera-uname'
TRACKER_HOST = 'tracker.archiveteam.org'


###########################################################################
# This section defines project-specific tasks.
#
# Simple tasks (tasks that do not need any concurrency) are based on the
# SimpleTask class and have a process(item) method that is called for
# each item.
class PrepareDirectories(SimpleTask):
    def __init__(self, warc_prefix):
        SimpleTask.__init__(self, "PrepareDirectories")
        self.warc_prefix = warc_prefix

    def process(self, item):
        item_name = item["item_name"]
        dirname = "/".join((item["data_dir"], item_name))

        if os.path.isdir(dirname):
            shutil.rmtree(dirname)

        os.makedirs(dirname)

        item["item_dir"] = dirname
        item["warc_file_base"] = "%s-%s-%s" % (self.warc_prefix, item_name,
            time.strftime("%Y%m%d-%H%M%S"))

        open("%(item_dir)s/%(warc_file_base)s.friends.txt" % item, "w").close()
        open("%(item_dir)s/%(warc_file_base)s.visitors.txt" % item, "w").close()


class MoveFiles(SimpleTask):
    def __init__(self):
        SimpleTask.__init__(self, "MoveFiles")

    def process(self, item):
        os.rename("%(item_dir)s/%(warc_file_base)s.friends.txt" % item,
            "%(data_dir)s/%(warc_file_base)s.friends.txt" % item)
        os.rename("%(item_dir)s/%(warc_file_base)s.visitors.txt" % item,
            "%(data_dir)s/%(warc_file_base)s.visitors.txt" % item)
 
        shutil.rmtree("%(item_dir)s" % item)


###########################################################################
# Initialize the project.
#
# This will be shown in the warrior management panel. The logo should not
# be too big. The deadline is optional.

project = Project(
    title="My Opera Usernames",
    project_html="""
    <img class="project-logo" alt="" src="http://i.imgur.com/S5Ubz6x.png" height="50" />
    <h2>My Opera <span class="links"><a href="http://my.opera.com/">Website</a> &middot; <a href="http://%s/%s/">Leaderboard</a></span></h2>
    <p><b>Opera</b> closes its social network.</p>
    """ % (TRACKER_HOST, TRACKER_ID)
    , utc_deadline=datetime.datetime(2014, 03, 01, 00, 00, 1)
)

pipeline = Pipeline(
    GetItemFromTracker("http://%s/%s" % (TRACKER_HOST, TRACKER_ID), downloader,
        VERSION),
    PrepareDirectories(warc_prefix="myopera-username"),
    ExternalProcess(
        'Scraper',
        [
        "python", "scraper.py",
        ItemInterpolation("%(item_name)s"),
        ItemInterpolation("%(item_dir)s/%(warc_file_base)s")
        ]
    ),
    PrepareStatsForTracker(
        defaults={ "downloader": downloader, "version": VERSION },
        file_groups={
            "data": [ 
                ItemInterpolation("%(item_dir)s/%(warc_file_base)s.friends.txt"),
                ItemInterpolation("%(item_dir)s/%(warc_file_base)s.visitors.txt"),
            ]
        }
    ),
    MoveFiles(),
    LimitConcurrent(NumberConfigValue(min=1, max=4, default="1",
        name="shared:rsync_threads", title="Rsync threads",
        description="The maximum number of concurrent uploads."),
        UploadWithTracker(
            "http://tracker.archiveteam.org/%s" % TRACKER_ID,
            downloader=downloader,
            version=VERSION,
            files=[
                ItemInterpolation("%(data_dir)s/%(warc_file_base)s.friends.txt"),
                ItemInterpolation("%(data_dir)s/%(warc_file_base)s.visitors.txt"),
            ],
            rsync_target_source_path=ItemInterpolation("%(data_dir)s/"),
            rsync_extra_args=[
                "--recursive",
                "--partial",
                "--partial-dir", ".rsync-tmp"
            ]
            ),
    ),
    SendDoneToTracker(
        tracker_url="http://%s/%s" % (TRACKER_HOST, TRACKER_ID),
        stats=ItemValue("stats")
    )
)

