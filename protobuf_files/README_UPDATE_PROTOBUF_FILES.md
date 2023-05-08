# Obtaining procedure:

1. Ensure protobuf_files exists in the main directory. This file should be in this location. 
2. (Optional) Backup any existing `.proto` files. There may have been breaking changes, and it is much easier to compare .proto files instead of their compiled versions. 
3. From the main directory, execute `inv pull_protobuf_files` it will dump all of the necessary proto files here. 


# Updating procedure

1. (Optional) Copy all existing files in `src/steam_network/protocol/messages/` to a backup directory. If you backed up the proto files in the obtain procedure, you may ignore this step. otherwise, they may be useful determining if any changes have occured. 
2. Make sure that your virtual environment has the `protobuf` library installed. If not then install it with the
version in the `requirements/app.txt` file.
3. Make sure your virtual environment has `invoke` installed. if not, install the version in `requirements/app.txt`
4. Make sure you have `protoc` installed. It should come with `protobuf`, but may not. 
5. To generate/update python files in `src/steam_network/protocol/messages/`
from main directory, run command: `inv generate-protobuf-messages`
6. If you received a warning log in the console that some of the messages already exist, check that the mentioned file
is not obsolete.
7. Check imports in `steam_network/protocol/protobuf_client.py`. Some messages could have moved or been renamed.
8. Build the plugin and check that it works, especially features which may be affected by changes in their protobuf
messages.

## Sources

* <https://github.com/steamdatabase/protobufs>
* <https://github.com/ValvePython/steam>
