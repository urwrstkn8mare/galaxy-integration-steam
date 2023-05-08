import os
import sys
import json
import tempfile
from shutil import rmtree
from distutils.dir_util import copy_tree

from urllib.request import urlopen #used to retrieve the proto files from github. 
from re import sub #used to replace some strings in the proto files to make them more python friendly
from http.client import HTTPResponse

from invoke import task
from galaxy.tools import zip_folder_to_file

with open(os.path.join("src", "manifest.json"), "r") as f:
    MANIFEST = json.load(f)

if sys.platform == 'win32':
    DIST_DIR = os.environ['localappdata'] + '\\GOG.com\\Galaxy\\plugins\\installed'
    PIP_PLATFORM = "win32"
    PYTHON_EXE = "python.exe"
    PROTOC_EXE = "protoc.exe"
elif sys.platform == 'darwin':
    DIST_DIR = os.path.realpath(os.path.expanduser("~/Library/Application Support/GOG.com/Galaxy/plugins/installed"))
    PIP_PLATFORM = "macosx_10_13_x86_64"  # @see https://github.com/FriendsOfGalaxy/galaxy-integrations-updater/blob/master/scripts.py
    PYTHON_EXE = "python"
    PROTOC_EXE = "protoc"

@task
def build(c, output='output', ziparchive=None):
    if os.path.exists(output):
        print('--> Removing {} directory'.format(output))
        rmtree(output)

    print('--> Fixing a pip issue, failing to import `BAR_TYPES` from `pip._internal.cli.progress_bars`')
    c.run(PYTHON_EXE + ' -m pip install -U pip==22.0.4')
    c.run('pip install -U pip==22.0.4 wheel pip-tools setuptools')

    # Firstly dependencies needs to be "flatten" with pip-compile as pip requires --no-deps if --platform is used
    print('--> Flattening dependencies to temporary requirements file')
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp:
        c.run(f'pip-compile requirements/app.txt --output-file=-', out_stream=tmp)

    # Then install all stuff with pip to output folder
    print('--> Installing with pip for specific version')
    args = [
        'pip', 'install',
        '-r', tmp.name,
        '--python-version', '37',
        '--platform', PIP_PLATFORM,
        '--target "{}"'.format(output),
        '--no-compile',
        '--no-deps'
    ]
    c.run(" ".join(args), echo=True)
    os.unlink(tmp.name)

    print('--> Copying source files')
    copy_tree("src", output)

    if ziparchive is not None:
        print('--> Compressing to {}'.format(ziparchive))
        zip_folder_to_file(output, ziparchive)

def _read_url(response :HTTPResponse) -> str:
    charset = response.headers.get_content_charset('utf-8')
    raw_data = response.read()
    return raw_data.decode(charset)

excluded_list = [
    "test_messages.proto",
    "gc.proto",
    "steammessages_webui_friends.proto",
    "steammessages_physicalgoods.proto",
    ]


#for whatever reason if i give this an _ in the name it can't find it. i have no idea why. so 
@task 
def PullProtobufFiles(c, silent=False):
    if (not os.path.exists("protobuf_files/protos/")):
        os.makedirs("protobuf_files/protos")


    with open("protobuf_files/protobuf_list.txt") as file:
        for line in file:
            #obtain the filename from the string. i'm being lazy, and stripping out the http:// stuff. 
            line = line.replace("\n", "")
            if (not silent):
                print("Retrieving: " + line)
            file_name = line.replace(r"https://raw.githubusercontent.com/SteamDatabase/SteamTracking/master/Protobufs/", "")
            response = urlopen(line)
            data = _read_url(response)

            if (not any(excluded in file_name for excluded in excluded_list)):
    
                if (".steamclient.proto" in file_name):
                    file_name = file_name.replace(".steamclient.proto", ".proto")
    
                if ("cc_generic_services" in data):
                    data = data.replace("cc_generic_services", "py_generic_services")
    
                if (".steamclient.proto" in data):
                    data = data.replace (".steamclient.proto", ".proto")
    
                data = 'syntax = "proto2";\n' + data

            with open("protobuf_files/protos/" + file_name, "w") as dest:
                dest.write(data)

@task
def ClearProtobufFiles(c):
    filelist = [ f for f in os.listdir("protobuf_files/protos") if f.endswith(".proto") ]
    for f in filelist:
        os.remove(os.path.join("protobuf_files/protos/", f))

@task
def GenerateProtobufMessages(c, genFile = True):
    if (genFile and not os.path.exists("protobuf_files/gen")):
        os.makedirs("protobuf_files/gen")
    out_dir = "./protobuf_files/gen/" if genFile else "src/steam_network/protocol/messages"
    all_files = " ".join(filter(lambda x : x.endswith(".proto"), os.listdir("protobuf_files/protos")))
    #all_files = " ".join(filter(lambda x : x.endswith(".proto"), map(lambda y: "protos/" + y, os.listdir("protobuf_files/protos"))))
    print(PROTOC_EXE + ' -I "protobuf_files/protos" ' +
        ' --python_out="' + out_dir +'" ' + all_files)
    c.run(
        PROTOC_EXE + ' -I "protobuf_files/protos"' +
        ' --python_out="' + out_dir +'" ' + all_files
    )


@task
def test(c):
    c.run('pytest')


@task
def install(c):
    dist_path = os.path.join(DIST_DIR, "steam_" + MANIFEST['guid'])
    build(c, output=dist_path)


@task
def pack(c):
    output = "steam_" + MANIFEST['guid']
    build(c, output=output, ziparchive='steam_v{}.zip'.format(MANIFEST['version']))
    rmtree(output)
