myopera-username-grab
=====================

** Not setup yet on tracker, please wait to run this! **

More information about the archiving project can be found on the [ArchiveTeam wiki page for the project](http://www.archiveteam.org/index.php?title=My_Opera)!

Setup instructions
=========================

Be sure to replace `YOURNICKHERE` with the nickname that you want to be shown as, on the tracker. You don't need to register it, just pick a nickname you like.

In most of the below cases, there will be a web interface running at http://localhost:8001/. If you don't know or care what this is, you can just ignore it - otherwise, it gives you a fancy view of what's going on.

**If anything goes wrong while running the commands below, please scroll down to the bottom of this page - there's troubleshooting information there.**

Running with a warrior
-------------------------

Follow the [instructions on the ArchiveTeam wiki](http://archiveteam.org/index.php?title=Warrior) for installing the Warrior, and select the "My Opera Discovery" project in the Warrior interface.

Running without a warrior
-------------------------

To run this outside the warrior, clone this repository and run:

    pip install seesaw

then start downloading with:

    run-pipeline pipeline.py --concurrent 2 YOURNICKHERE

For more options, run:

    run-pipeline --help
    
Running multiple instances on different IPs
-------------------------

This is not currently supported.

Distribution-specific setup
-------------------------

### For Debian/Ubuntu:

    adduser --system --group --shell /bin/bash archiveteam
    apt-get install -y git-core screen python-pip bzip2
    pip install seesaw
    su -c "cd /home/archiveteam; git clone https://github.com/MithrandirAgain/myopera-username-grab.git" archiveteam
    screen su -c "cd /home/archiveteam/myopera-username-grab/; run-pipeline pipeline.py --concurrent 2 --address '127.0.0.1' YOURNICKHERE" archiveteam
    [... ctrl+A D to detach ...]
    
### For CentOS:

Ensure that you have the CentOS equivalent of bzip2 installed as well. You might need the EPEL repository to be enabled.

    yum -y install python-pip
    pip install seesaw
    [... pretty much the same as above ...]

### For openSUSE:

    zypper install screen python-pip bzip2 python-devel gcc make
    pip install seesaw
    [... pretty much the same as above ...]

### For OS X:

You need Homebrew. Ensure that you have the OS X equivalent of bzip2 installed as well.

    brew install python
    pip install seesaw
    [... pretty much the same as above ...]

**There is a known issue with some packaged versions of rsync. If you get errors during the upload stage, myopera-username-grab will not work with your rsync version.**

This supposedly fixes it:

    alias rsync=/usr/local/bin/rsync

### For Arch Linux:

Ensure that you have the Arch equivalent of bzip2 installed as well.

1. Make sure you have `python-pip2` installed.
2. Run `pip2 install seesaw`.
3. Modify the run-pipeline script in seesaw to point at `#!/usr/bin/python2` instead of `#!/usr/bin/python`.
4. `adduser --system --group --shell /bin/bash archiveteam`
5. `screen su -c "cd /home/archiveteam/myopera-username-grab/; run-pipeline pipeline.py --concurrent 10 --address '127.0.0.1' YOURNICKHERE" archiveteam`

### For FreeBSD:

No known instructions. Try and see if it works!

Troubleshooting
=========================

Broken? These are some of the possible solutions:
    
### ImportError: No module named seesaw

If you're sure that you followed the steps to install `seesaw`, permissions on your module directory may be set incorrectly. Try the following:

    chmod o+rX -R /usr/local/lib/python2.7/dist-packages
