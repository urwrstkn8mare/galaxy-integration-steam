import os
import sys
import json
import tempfile
from shutil import rmtree
from distutils.dir_util import copy_tree

from invoke import task
from galaxy.tools import zip_folder_to_file

with open(os.path.join("src", "manifest.json"), "r") as f:
    MANIFEST = json.load(f)

if sys.platform == 'win32':
    DIST_DIR = os.environ['localappdata'] + '\\GOG.com\\Galaxy\\plugins\\installed'
    PIP_PLATFORM = "win32"
elif sys.platform == 'darwin':
    DIST_DIR = os.path.realpath(os.path.expanduser("~/Library/Application Support/GOG.com/Galaxy/plugins/installed"))
    PIP_PLATFORM = "macosx_10_13_x86_64"  # @see https://github.com/FriendsOfGalaxy/galaxy-integrations-updater/blob/master/scripts.py

@task
def build(c, output='output', ziparchive=None):
    if os.path.exists(output):
        print('--> Removing {} directory'.format(output))
        rmtree(output)

    print('--> Fixing a pip issue, failing to import `BAR_TYPES` from `pip._internal.cli.progress_bars`')
    c.run('python.exe -m pip install -U pip==22.0.4')
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


@task
def generate_protobuf_messages(c):
    c.run(
        'protoc -I"protobuf_files"' +
        ' --python_out="src/steam_network/protocol/messages"' +
        ' protobuf_files/service_community.proto' +
        ' protobuf_files/service_cloudconfigstore.proto' +
        ' protobuf_files/encrypted_app_ticket.proto' +
        ' protobuf_files/enums.proto' +
        ' protobuf_files/steammessages_base.proto' +
        ' protobuf_files/steammessages_chat.steamclient.proto' +
        ' protobuf_files/steammessages_client_objects.proto' +
        ' protobuf_files/steammessages_clientserver.proto' +
        ' protobuf_files/steammessages_clientserver_2.proto' +
        ' protobuf_files/steammessages_clientserver_appinfo.proto' +
        ' protobuf_files/steammessages_clientserver_friends.proto' +
        ' protobuf_files/steammessages_clientserver_login.proto' +
        ' protobuf_files/steammessages_clientserver_userstats.proto' +
        ' protobuf_files/steammessages_player.steamclient.proto' +
        ' protobuf_files/steammessages_unified_base.steamclient.proto'
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
