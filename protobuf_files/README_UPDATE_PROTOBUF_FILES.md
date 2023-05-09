# Obtaining, Parsing, and Recompiling Protobuf Files:
Unfortunately, Steam has made this difficult. They've moved around various functions, and now multiple functions we safely used before are in new locations, and the imports for these files cause conflicts with one another. As such, we've divided our protobuf file list into 3 Categories: Safe, Conflicting, and merged (aka Merged). The Safe and Merged files will be converted to .py files and used in the code. The conflicting ones must manually be parsed and the results put in the 

## Obtaining procedure:

1. Ensure protobuf_files exists in the main directory. This file should be in this location. 
2. (Optional) Backup any existing `.proto` files. There may have been breaking changes, and it is much easier to compare .proto files instead of their compiled versions. 
3. From the main directory, execute one of the following commands
  - `inv PullSafeProtobufFiles` will retrieve the files that do not contain conflicts with one another. Unless it is necessary to add functionality from the conflicting files, this is the recommended command. Safe files go in the `protobuf_files/protos` file. 
  - `inv PullConflictingProtobufFiles` will retrieve the files that conflict with the other files. These protobuf files need to be parsed manually, with the necessary messages and classes put into a new file. Conflicting files go in the `protobuf_files/conflicts` folder
  - `inv PullAllProtobufFiles` will retrieve both the regular and conflicting files. It may be a good idea to use this to get a general look at everything.

## Parsing Procedure (Optional)
The Pull commands will automatically parse and/or the files so they do not contain unnecessary files. However, the conflicting files will not be updated as is. Therefore, it is only necessary to do this if you need additional functionality from a conflicting file. 
1. Check if the classes or methods you need are in the `protobuf_files/merged/resolved_service_messages.proto` file. If they are, overwrite them if needed.
2. If not, decide if you are going to merge them into `protobuf_files/merged/resolved_service_messages.proto`, or create a new .proto file in `protobuf_files/merged/`


## Updating procedure

The process here is a bit more involved 


1. (Optional) Copy all existing files in `src/steam_network/protocol/messages/` to a backup directory. If you backed up the proto files in the obtain procedure, you may ignore this step. otherwise, they may be useful determining if any changes have occured. 
2. Make sure that your virtual environment has the `protobuf` library installed. If not then install it with the
version in the `requirements/app.txt` file.
3. Make sure your virtual environment has `invoke` installed. if not, install the version in `requirements/app.txt`
4. Make sure you the right `protoc` installed. Protobuf version 3.20 and up introduced a breaking change to how the proto files are compiled. We should support it, but imo it's easier to read the statically-defined files. You can find the correct protoc files here: https://github.com/protocolbuffers/protobuf/releases/tag/v3.18.1
5. Make sure protoc is accessible from your build directory. If using windows, make sure the folder containing `protoc.exe` is in your environmental path. If on *nix, make sure it's in either `/home/` or otherwise accessible to you. 
6. If you retrieve the conflicting files, make sure to obtain any necessary classes or messages and place them into the `protobuf_files/merged` folder. These should be put in the `steammessages_merged.proto` file (overwrite any out of date functions) unless they are drastic or it provides more clarity. Make sure not to have the same definitions in multiple files.
7. Run `inv GenerateProtobufMessages` will convert all `.proto` files found in the `protobuf_files/protos` and `protobuf_files/merged` directories into their `.py` form. These are placed in the `protobuf_files/gen` folder by default so you can compare against the compile files in `steam_network/protocol/messages` but you can force them there directly by setting `genFile=False`
8. If you did not overwrite the messages directory, you can compare the files to see if anything changed. `Diff` or `git diff` can be useful here. If you did, skip to step 10.
9. Move or copy the files from `protobuf_files/gen` to `steam_network/protocol/protobuf_client.py`
10. Check imports in `steam_network/protocol/protobuf_client.py`. Some messages could have moved or been renamed.
11. Build the plugin and check that it works, especially features which may be affected by changes in their protobuf
messages.

## Sources

* <https://github.com/steamdatabase/protobufs>
* <https://github.com/ValvePython/steam>
