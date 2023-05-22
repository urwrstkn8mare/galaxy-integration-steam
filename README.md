# Steam Integration

GOG Galaxy 2.0 Community integration for Steam.

This is a fork of the repository from FriendsOfGalaxy, intended to continue development until they resume their work.

**This is unofficial and purely maintained by fans!**

### Alpha Testers: Please see Installation Steps below Setup For Developers

## Setup (For Developers)
* Download [Python 3.7.9 32-bit][Python379]
* Install it with the defaults
* Create a new virtual env:
    - If you only have Python 3.7.9<br/>
    `python -m venv .venv`
    - If you have multiple Python versions installed (assumes you have `py` as well)<br/>
    `py -3.7 -m venv .venv`
* Activate the virtual env 
  - Windows, Powershell:<br/>
  `.\.venv\Scripts\activate.ps1`
  - MacOS, terminal:<br/>
  `.venv/Scripts/activate`
* Install the dev dependencies:<br/>
  `pip install -r requirements/dev.txt`
* Make your edits
* Update the protobufs (See README_UPDATE_PROTOBUF_FILES.md for more info)
  Take notice of the initial diff between the files in `protobuf_files` and `protobuf_files/orig`
  Generating the python files is done via:
  `inv GenerateProtobufMessages`
* Build your edits:
  `inv build`
* Test your edits:
  `inv test`
* Install your edits for a local test:
  `inv install`
* Build a release package (zip):
  `inv pack`

## Installation (non-developers)

*~~The latest release should be available for download via the "Connect" button in Galaxy~~*
We aren't ready to publish this project to Galaxy just yet. We have the tools to do so, but the code is not stable enough for us to consider that just yet. 

In the meantime, we've provided a simplified version of the developer install process that only does the bare minimum to install the plugin. There are only a few commands you need to run, but if you want to know what they do, they are documented above each command. A tl;dr: version is below it.

Please do the following:
* Download or clone this repo. If you download a zip, make sure to extract it. You need to be in the main directory for this to work. 
* Download [Python 3.7.9 32-bit][Python379].
  <br> If you have another version of python installed, make sure `install py` is checked.
  <br> This makes it easier to select which version of python you are using and we need our virtual environment in 3.7.9.
  <br> If using Windows, make sure you have enabled the setting that `adds Python to the PATH environmental variable`.
  <br> These should be the default settings, but make sure anyway.
* Create a new virtual env:
    - If you only have python 3.7.9<br/>
    `python -m venv .venv`
    - IF you have multiple python versions installed (assumes you have `py` as well)<br/>
    `py -3.7 -m venv .venv`
* Activate the virtual env 
  - Windows, Powershell:<br/>
  `.\.venv\Scripts\activate.ps1`
  - MacOS, terminal:<br/>
  `.venv/Scripts/activate.sh`
* Use Pip to get the python tools we need to install the plugin. These will only be applied to the venv you created earlier:<br/>
  `pip install -r requirements/install.txt`
* Install the plugin. It should work if you have deleted the original plugin, but will patch it if it is there.<br/>
  `inv install`

### Installation (non-dev, Tl;Dr):

<b>Windows (Powershell recommended)</b>
```
echo You must have installed python 3.7.9 (32 bit). If not, the rest of this won't work.
py.exe -3.7 -m venv .venv
echo if the previous command did not work, you do not have py installed or py is not in your PATH. If you only have python 3.7.9, run the next command. If it worked, skip the next command.
python.exe -m venv .venv
echo virtual environment is installed. on to the next step.
.\.venv\Scripts\activate.ps1
pip install -r requirements/install.txt
inv install
```

<b>MacOS</b> (assumes your shell is bash, which is the default. if you are good enough to change that, you can figure out how to run these)
```
echo I have installed python 3.7.9 (MacOS). If not, the rest of this won't work.
py -3.7 -m venv .venv
echo if the previous command did not work, you do not have py installed or py is not in your PATH. If you only have python 3.7.9, run the next command. If it worked, skip the next command.
python -m venv .venv
echo virtual environment is installed. on to the next step.
./.venv/Scripts/activate.sh
pip install -r requirements/install.txt
inv install
```

### Install Error fixes:
If `inv install` throws a bunch of errors, make sure you have the proper python venv set up. It should complain about `getargspec`. If this happens, you created the wrong virtual environment. You can either delete .venv and reinstall it, or create a new virtual environment with a different name and use that. make sure you use `py -3.7` when creating your venv. If you don't have py, get it. You can specify the full path to python 3.7 instead if you want, but that's harder to do and harder to explain here. 

## Why this fork?

Well, without being too complicated, Steam changed how they do authentication. We used to be able to use one call and magically get a lot of info we needed. But, if we're being honest, it was a little insecure, and it easy. While we were using it for legitimate purposes, not everyone else was, and one of Valve's greatest deterrence to botting or DOS attacks (etc) is making things difficult. The new workflow uses a significant back-and-forth between a Steam Server and ourselves, closely resembling a common web form of authentication called OAuth2. This meant a lot of under-the-hood changes. 

## Credits

### Current Version:
This is a fork of https://github.com/FriendsOfGalaxy/galaxy-integration-steam

The new Authorization flow implementation is heavily influenced by SteamKit. https://github.com/SteamRE/SteamKit<br/>
While we have not utilized their source code, they have implemented the new authentication workflow before we did, and we used their knowledge of how to do so in order to implement it ourselves. If you are doing anything steam related in C#, you should check them out; their project has far more features than our own.

Some work was influenced by ValvePython. https://github.com/ValvePython/steam<br/>
Our projects do the same thing, but use different methods (we use asyncio, they use gevent, for example). Both projects were working on the new Auth Flow simultaneously, with little collaboration between us. That said, their scope is much larger than our own and lets you do a lot more things. If you are looking for a python means of implementing a steam network authentication, you should use their work instead.

### The names of individual developers will appear here, soon(ish). Any thanks can be directed there

### Original Version:

Original Plugin was based on work and research done by others:
* https://github.com/prncc/steam-scraper
* https://github.com/rhaarm/steam-scraper
* https://github.com/mulhod/steam_reviews
* https://github.com/summersb92/aeolipile
* https://github.com/rcpoison/steam-scraper
* https://github.com/chmccc/steam-scraper


[Python379]: https://www.python.org/downloads/release/python-379/