# Updating procedure

1. Move all new `.proto` files to `protobuf_files/`
2. Make sure that your virtual environment has the `protobuf` library installed. If not then install it with the
version in the `requirements/app.txt` file.
3. To generate/update python files in `src/steam_network/protocol/messages/`
from above directory, run command: `inv generate-protobuf-messages`
4. If you received a warning log in the console that some of the messages already exist, check that the mentioned file
is not obsolete.
5. Check imports in `steam_network/protocol/protobuf_client.py`. Some messages could have moved or been renamed.
6. Build the plugin and check that it works, especially features which may be affected by changes in their protobuf
messages.

## Sources

* <https://github.com/steamdatabase/protobufs>
* <https://github.com/ValvePython/steam>
